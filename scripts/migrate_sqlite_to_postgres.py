"""
Migra los datos de la BD SQLite actual a PostgreSQL.

Uso (dentro del container de Coolify, DESPUÉS de configurar DATABASE_URL a PG):
    cd /app && python scripts/migrate_sqlite_to_postgres.py

Cómo funciona:
1. Abre la SQLite actual como origen (por default /app/instance/ticketdesk_v2.db).
2. Se conecta a PostgreSQL usando DATABASE_URL del env.
3. Crea el schema en PostgreSQL con db.create_all() (mismo modelo).
4. Copia todos los registros tabla por tabla.
5. Resetea las secuencias de IDs para que próximos INSERT no colisionen.

Flags:
    --sqlite /ruta/otra.db     ruta alternativa de la SQLite origen
    --dry-run                  no escribe nada, solo cuenta filas
    --skip-tables tabla1,tabla2  no copiar estas tablas (útil para saltear system_log grande)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Permitir importar app.py desde /app
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default="/app/instance/ticketdesk_v2.db",
                        help="Path a la BD SQLite origen")
    parser.add_argument("--dry-run", action="store_true", help="Solo contar filas sin escribir")
    parser.add_argument("--skip-tables", default="",
                        help="Lista separada por comas de tablas a saltear")
    parser.add_argument("--truncate-first", action="store_true",
                        help="TRUNCATE todas las tablas destino antes de copiar. Necesario si PG ya tiene datos de init_db()")
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.exists():
        # Fallback local
        alt = ROOT / "instance" / "ticketdesk_v2.db"
        if alt.exists():
            sqlite_path = alt
        else:
            print(f"[ERROR] No se encontró la SQLite: {args.sqlite}")
            sys.exit(1)

    skip_tables = {t.strip() for t in args.skip_tables.split(",") if t.strip()}

    # Verificar que DATABASE_URL apunte a PostgreSQL
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url.startswith(("postgres://", "postgresql://")):
        print(f"[ERROR] DATABASE_URL no apunta a PostgreSQL: {db_url}")
        print("        Configura DATABASE_URL en Coolify a postgresql://... antes de correr esto.")
        sys.exit(1)

    print(f"[INFO] Origen SQLite : {sqlite_path}")
    print(f"[INFO] Destino PG    : {db_url.split('@')[-1] if '@' in db_url else db_url}")
    if args.dry_run:
        print("[INFO] MODO DRY-RUN — no se escribirá nada")
    print()

    # Cargar la app (esto conecta SQLAlchemy a la DATABASE_URL que es PG ahora)
    from app import app, db
    from sqlalchemy import inspect, text

    with app.app_context():
        # 1) Crear schema en PostgreSQL
        if not args.dry_run:
            print("[STEP 1] Creando tablas en PostgreSQL...")
            db.create_all()
            print("[OK] Schema creado")
            print()

            # 1b) Truncar tablas destino si se pidio (usualmente si init_db() ya poblo datos)
            if args.truncate_first:
                print("[STEP 1b] Truncando tablas destino (--truncate-first)...")
                insp_tmp = inspect(db.engine)
                all_tables = insp_tmp.get_table_names()
                if all_tables:
                    truncate_list = ', '.join(f'"{t}"' for t in all_tables)
                    db.session.execute(text(f"TRUNCATE {truncate_list} RESTART IDENTITY CASCADE"))
                    db.session.commit()
                    print(f"[OK] {len(all_tables)} tablas truncadas")
                print()

        # 2) Abrir SQLite como origen
        import sqlite3
        src = sqlite3.connect(str(sqlite_path))
        src.row_factory = sqlite3.Row

        # 3) Listar tablas de SQLite (excepto meta y skip)
        src_tables = [
            r[0] for r in src.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]

        # 4) Filtrar por lo que existe en el modelo destino
        insp = inspect(db.engine)
        dst_tables = set(insp.get_table_names())

        # Orden lógico para respetar FKs: primero tablas independientes
        priority_first = ["companies", "users", "subroles", "tags", "botknowledge", "templates"]
        ordered = [t for t in priority_first if t in src_tables] + \
                  [t for t in src_tables if t not in priority_first]

        summary = []

        for table in ordered:
            if table in skip_tables:
                print(f"[SKIP] Tabla {table} (por --skip-tables)")
                summary.append((table, 0, 0, "skipped"))
                continue
            if table not in dst_tables:
                print(f"[SKIP] Tabla {table} no existe en el modelo PG destino")
                summary.append((table, 0, 0, "no destination"))
                continue

            # Contar filas origen
            src_count = src.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if src_count == 0:
                print(f"[--- ] {table}: vacia en origen")
                summary.append((table, 0, 0, "empty"))
                continue

            # Columnas comunes (por si el modelo PG tiene columnas que la SQLite no)
            src_cols = [r[1] for r in src.execute(f"PRAGMA table_info({table})").fetchall()]
            dst_cols = {c["name"] for c in insp.get_columns(table)}
            common = [c for c in src_cols if c in dst_cols]

            if args.dry_run:
                print(f"[DRY ] {table}: {src_count} filas listas para copiar")
                summary.append((table, src_count, 0, "dry-run"))
                continue

            # Copiar en batches para no explotar memoria
            print(f"[COPY] {table}: {src_count} filas...", end=" ", flush=True)
            copied = 0
            batch_size = 500
            cols_sql = ", ".join(f'"{c}"' for c in common)
            placeholders = ", ".join(f":{c}" for c in common)
            insert_sql = text(f'INSERT INTO "{table}" ({cols_sql}) VALUES ({placeholders})')

            batch = []
            for row in src.execute(f"SELECT {', '.join(common)} FROM {table}"):
                batch.append({c: row[c] for c in common})
                if len(batch) >= batch_size:
                    db.session.execute(insert_sql, batch)
                    copied += len(batch)
                    batch = []
            if batch:
                db.session.execute(insert_sql, batch)
                copied += len(batch)
            db.session.commit()
            print(f"OK ({copied} copiadas)")
            summary.append((table, src_count, copied, "ok"))

        src.close()

        # 5) Resetear las secuencias de IDs (PG usa SERIAL)
        if not args.dry_run:
            print()
            print("[STEP 3] Reseteando secuencias de IDs...")
            for table in dst_tables:
                try:
                    # PostgreSQL: SELECT setval(pg_get_serial_sequence(...), max(id))
                    q = text(f"""
                        SELECT setval(
                            pg_get_serial_sequence('{table}', 'id'),
                            COALESCE((SELECT MAX(id) FROM "{table}"), 1),
                            (SELECT MAX(id) IS NOT NULL FROM "{table}")
                        )
                    """)
                    db.session.execute(q)
                except Exception as e:
                    # La tabla puede no tener columna 'id' (raro pero posible)
                    pass
            db.session.commit()
            print("[OK] Secuencias reseteadas")

        # 6) Resumen
        print()
        print("=" * 70)
        print("RESUMEN")
        print("=" * 70)
        print(f"{'TABLA':<30} {'ORIGEN':>10} {'COPIADAS':>10}  ESTADO")
        print("-" * 70)
        for table, orig, cop, status in summary:
            print(f"{table:<30} {orig:>10} {cop:>10}  {status}")
        print("=" * 70)
        total_orig = sum(s[1] for s in summary)
        total_cop = sum(s[2] for s in summary)
        print(f"{'TOTAL':<30} {total_orig:>10} {total_cop:>10}")


if __name__ == "__main__":
    main()
