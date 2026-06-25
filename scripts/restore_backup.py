"""
Restaurar la BD de DeskEli desde un backup cifrado o plano.

Soporta:
  - backups/.db.gz.enc  (gzip + Fernet, formato actual)
  - backups/.db.gz      (gzip plano, formato legacy)

Uso:
  python scripts/restore_backup.py backups/ticketdesk_backup_YYYYMMDD_HHMMSS.db.gz.enc
  python scripts/restore_backup.py --dest instance/ticketdesk_v2.db backups/<archivo>

Para descifrar requiere DB_ENCRYPTION_KEY en el .env.
"""
from __future__ import annotations

import argparse
import gzip
import shutil
import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from crypto_utils import init_crypto, decrypt_bytes, has_key  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("backup_file", help="Ruta al archivo de backup (.db.gz o .db.gz.enc)")
    parser.add_argument("--dest", default=None,
                        help="BD destino (por defecto: instance/ticketdesk_v2.db)")
    parser.add_argument("--force", action="store_true",
                        help="Sobrescribir la BD destino sin pedir confirmación")
    args = parser.parse_args()

    backup_path = Path(args.backup_file)
    if not backup_path.exists():
        print(f"[ERROR] No existe el archivo: {backup_path}")
        sys.exit(1)

    # Destino por defecto: misma ruta que usa la app
    dest = Path(args.dest) if args.dest else ROOT / "instance" / "ticketdesk_v2.db"
    dest.parent.mkdir(exist_ok=True)

    print(f"[INFO] Backup origen : {backup_path}")
    print(f"[INFO] BD destino    : {dest}")

    is_encrypted = backup_path.name.endswith(".enc")
    if is_encrypted:
        init_crypto(is_production=False)
        if not has_key():
            print("[ERROR] El backup está cifrado pero DB_ENCRYPTION_KEY no está disponible.")
            sys.exit(1)

    if dest.exists() and not args.force:
        resp = input(f"[ATENCIÓN] {dest} existe. ¿Sobrescribir? [s/N] ")
        if resp.lower() not in ("s", "y", "yes", "si", "sí"):
            print("Cancelado.")
            sys.exit(0)

    # Backup de seguridad de la BD destino actual
    if dest.exists():
        safety = dest.with_suffix(dest.suffix + ".pre_restore.bak")
        shutil.copy2(dest, safety)
        print(f"[OK] Safety backup creado: {safety}")

    # Leer payload
    payload = backup_path.read_bytes()
    if is_encrypted:
        try:
            payload = decrypt_bytes(payload)
            print("[OK] Backup descifrado")
        except Exception as e:
            print(f"[ERROR] No se pudo descifrar (clave incorrecta?): {e}")
            sys.exit(1)

    # Descomprimir y escribir
    try:
        with gzip.GzipFile(fileobj=BytesIO(payload), mode="rb") as gz:
            with open(dest, "wb") as out:
                shutil.copyfileobj(gz, out)
    except Exception as e:
        print(f"[ERROR] No se pudo descomprimir: {e}")
        sys.exit(1)

    print(f"[DONE] BD restaurada en {dest} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
