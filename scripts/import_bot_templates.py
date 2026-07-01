"""
Importa la base de conocimiento del bot y plantillas desde el JSON exportado.

Uso:
  python scripts/import_bot_templates.py                              # usa data/bot_templates_export.json
  python scripts/import_bot_templates.py --file otro.json
  python scripts/import_bot_templates.py --mode replace               # borra y reimporta (default: merge)

Modos:
  merge (default): agrega registros nuevos, saltea los que ya existen (por keyword+question / name+company)
  replace        : BORRA todo el contenido de bot_knowledge y templates y reemplaza con el JSON

Ejecutar en el Terminal de Coolify:
  cd /app && python scripts/import_bot_templates.py
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_db() -> Path:
    """Localiza la BD del container o local."""
    candidates = [
        Path("/app/instance/ticketdesk_v2.db"),  # container Coolify
        ROOT / "instance" / "ticketdesk_v2.db",  # local
        ROOT / "ticketdesk_v2.db",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"No se encontró la BD. Buscado en: {candidates}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=str(ROOT / "data" / "bot_templates_export.json"))
    parser.add_argument("--db", default=None)
    parser.add_argument("--mode", choices=("merge", "replace"), default="merge")
    args = parser.parse_args()

    src = Path(args.file)
    if not src.exists():
        print(f"[ERROR] Archivo JSON no encontrado: {src}")
        sys.exit(1)

    db_path = Path(args.db) if args.db else find_db()
    print(f"[INFO] BD destino : {db_path}")
    print(f"[INFO] Fuente JSON: {src}")
    print(f"[INFO] Modo       : {args.mode}")

    with open(src, "r", encoding="utf-8") as f:
        payload = json.load(f)

    conn = sqlite3.connect(str(db_path))

    # Modo replace: borrar todo primero
    if args.mode == "replace":
        conn.execute("DELETE FROM bot_knowledge")
        conn.execute("DELETE FROM templates")
        print("[INFO] Modo replace: tablas vaciadas")

    # ─── bot_knowledge ───
    kb_added = 0
    kb_skipped = 0
    for row in payload.get("bot_knowledge", []):
        keywords = row.get("keywords")
        question = row.get("question")
        if args.mode == "merge":
            existing = conn.execute(
                "SELECT id FROM bot_knowledge WHERE keywords=? AND question=?",
                (keywords, question),
            ).fetchone()
            if existing:
                kb_skipped += 1
                continue
        conn.execute(
            """INSERT INTO bot_knowledge (keywords, question, answer, category, priority, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                row.get("keywords"),
                row.get("question"),
                row.get("answer"),
                row.get("category"),
                row.get("priority"),
                row.get("created_at"),
            ),
        )
        kb_added += 1

    # ─── templates ───
    tpl_added = 0
    tpl_skipped = 0
    # Detectar columnas reales de la tabla destino
    tpl_cols_dest = {r[1] for r in conn.execute("PRAGMA table_info(templates)").fetchall()}

    for row in payload.get("templates", []):
        name = row.get("name")
        company = row.get("company")
        if args.mode == "merge":
            existing = conn.execute(
                "SELECT id FROM templates WHERE name=? AND (company=? OR (company IS NULL AND ? IS NULL))",
                (name, company, company),
            ).fetchone()
            if existing:
                tpl_skipped += 1
                continue

        # Solo insertar columnas que existan en la tabla destino
        insertable = {k: v for k, v in row.items() if k in tpl_cols_dest}
        cols = ", ".join(insertable.keys())
        placeholders = ", ".join("?" for _ in insertable)
        conn.execute(
            f"INSERT INTO templates ({cols}) VALUES ({placeholders})",
            list(insertable.values()),
        )
        tpl_added += 1

    conn.commit()
    conn.close()

    print()
    print("=" * 60)
    print(f"[OK] bot_knowledge: {kb_added} agregados, {kb_skipped} ya existian")
    print(f"[OK] templates    : {tpl_added} agregados, {tpl_skipped} ya existian")
    print("=" * 60)


if __name__ == "__main__":
    main()
