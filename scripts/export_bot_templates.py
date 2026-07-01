"""
Exporta la base de conocimiento del bot y las plantillas a un JSON versionable.

Uso:
  python scripts/export_bot_templates.py                    # exporta a data/bot_templates_export.json
  python scripts/export_bot_templates.py --out otra_ruta.json

El JSON queda incluido en el repo (data/) para poder importarlo en otros deploys.
NO contiene secretos ni datos personales — solo respuestas del bot y plantillas.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_db() -> Path:
    """Localiza la BD activa."""
    candidates = [
        ROOT / "instance" / "ticketdesk_v2.db",
        ROOT / "ticketdesk_v2.db",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"No se encontró la BD. Buscado en: {candidates}")


def row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None, help="Ruta a la BD SQLite (autodetecta si no se pasa)")
    parser.add_argument("--out", default=str(ROOT / "data" / "bot_templates_export.json"))
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else find_db()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] BD origen: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    payload = {
        "_meta": {
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "source_db": str(db_path),
            "format_version": "1",
        },
        "bot_knowledge": [],
        "templates": [],
    }

    # Bot knowledge
    for row in conn.execute("SELECT * FROM bot_knowledge ORDER BY id"):
        d = row_to_dict(row)
        d.pop("id", None)  # el id lo genera el destino
        payload["bot_knowledge"].append(d)

    # Templates
    for row in conn.execute("SELECT * FROM templates ORDER BY id"):
        d = row_to_dict(row)
        d.pop("id", None)
        payload["templates"].append(d)

    conn.close()

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    print(f"[OK] Exportado a {out_path}")
    print(f"     - bot_knowledge : {len(payload['bot_knowledge'])} filas")
    print(f"     - templates     : {len(payload['templates'])} filas")


if __name__ == "__main__":
    main()
