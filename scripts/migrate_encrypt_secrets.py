"""
Cifra los secretos en BD que todavía están en texto plano.

Campos cubiertos:
  - companies.ldap_bind_password
  - companies.smtp_password
  - mailbox_configs.imap_password
  - mailbox_configs.oauth_client_secret

Es idempotente: si un valor ya tiene prefijo 'enc:v1:' no lo toca.
Hace backup de la BD antes de escribir.

Uso:
  cd <raíz del proyecto>
  python scripts/migrate_encrypt_secrets.py            # migración real
  python scripts/migrate_encrypt_secrets.py --dry-run  # solo reporte
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Permitir importar crypto_utils desde la raíz
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from crypto_utils import init_crypto, encrypt_secret, is_encrypted  # noqa: E402

TABLES = [
    ("companies", "id", ["ldap_bind_password", "smtp_password"]),
    ("mailbox_configs", "id", ["imap_password", "oauth_client_secret"]),
]


def find_active_db() -> Path:
    """Devuelve la BD que usa la app (resuelve DATABASE_URL relativo a instance/)."""
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("sqlite:///"):
        rel = db_url.replace("sqlite:///", "", 1)
        candidates = [
            ROOT / "instance" / rel,
            ROOT / rel,
        ]
        for p in candidates:
            if p.exists():
                return p
    # Fallback común
    for p in [ROOT / "instance" / "ticketdesk_v2.db", ROOT / "ticketdesk_v2.db"]:
        if p.exists():
            return p
    raise FileNotFoundError("No se encontró la BD SQLite (instance/ticketdesk_v2.db ni raíz).")


def backup_db(db_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = db_path.with_suffix(db_path.suffix + f".pre_encrypt_{stamp}.bak")
    shutil.copy2(db_path, bak)
    return bak


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="No escribe; solo reporta.")
    args = parser.parse_args()

    # Inicializar crypto en modo no-producción (la migración corre offline)
    init_crypto(is_production=False)
    if not os.getenv("DB_ENCRYPTION_KEY"):
        print("[ERROR] DB_ENCRYPTION_KEY no está definida en .env — abortar.")
        sys.exit(1)

    db_path = find_active_db()
    print(f"[INFO] BD detectada: {db_path}")

    if not args.dry_run:
        bak = backup_db(db_path)
        print(f"[INFO] Backup creado: {bak}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    total_changed = 0

    for table, pk, columns in TABLES:
        # Verificar columnas que realmente existen
        existing_cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        cols_to_process = [c for c in columns if c in existing_cols]
        if not cols_to_process:
            print(f"[SKIP] Tabla {table}: no tiene ninguna de las columnas {columns}")
            continue

        select_cols = ", ".join([pk] + cols_to_process)
        rows = conn.execute(f"SELECT {select_cols} FROM {table}").fetchall()
        print(f"\n[INFO] Procesando {table}: {len(rows)} filas")

        for row in rows:
            row_id = row[pk]
            updates = {}
            for col in cols_to_process:
                current = row[col]
                if current is None or current == "":
                    continue  # nada que cifrar
                if is_encrypted(current):
                    continue  # ya está cifrado, saltar
                updates[col] = encrypt_secret(current)

            if updates:
                cols_str = ", ".join(f"{c}=?" for c in updates)
                values = list(updates.values()) + [row_id]
                msg = f"  - {table}#{row_id}: cifrar {list(updates.keys())}"
                if args.dry_run:
                    print(f"[DRY] {msg}")
                else:
                    conn.execute(f"UPDATE {table} SET {cols_str} WHERE {pk}=?", values)
                    print(f"[OK ] {msg}")
                total_changed += 1

    if not args.dry_run:
        conn.commit()
    conn.close()

    print(f"\n[DONE] Filas modificadas: {total_changed}" + (" (dry-run)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
