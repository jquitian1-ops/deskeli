"""
Importa artículos de KB desde scripts/kb_articles_seed.json a la BD.
Idempotente: si el slug ya existe, salta el artículo.

Uso:
    python scripts/import_kb_articles.py                  # Importa como globales (company=None)
    python scripts/import_kb_articles.py --company eliot  # Importa solo para una empresa
    python scripts/import_kb_articles.py --author 1       # Usa user_id 1 como autor
    python scripts/import_kb_articles.py --dry-run        # Muestra qué haría sin insertar
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

# Añadir raíz del proyecto al path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import app, db, KnowledgeArticle, User


def slugify(text: str, max_len: int = 200) -> str:
    if not text:
        return 'articulo'
    txt = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    txt = txt.lower()
    txt = re.sub(r'[^a-z0-9]+', '-', txt).strip('-')
    return (txt or 'articulo')[:max_len]


def unique_slug(base: str) -> str:
    slug = base
    n = 2
    while KnowledgeArticle.query.filter_by(slug=slug).first():
        slug = f"{base}-{n}"
        n += 1
    return slug


def main():
    parser = argparse.ArgumentParser(description="Importa artículos KB desde JSON")
    parser.add_argument('--file', default='scripts/kb_articles_seed.json',
                        help='Ruta al JSON (default: scripts/kb_articles_seed.json)')
    parser.add_argument('--company', default=None,
                        help='Company code (eliot/pash/primatela). Default: None = global')
    parser.add_argument('--author', type=int, default=None,
                        help='user_id para author_id. Default: primer admin encontrado')
    parser.add_argument('--dry-run', action='store_true',
                        help='No inserta, solo reporta')
    args = parser.parse_args()

    json_path = ROOT / args.file
    if not json_path.exists():
        print(f"[ERROR] Archivo no encontrado: {json_path}")
        sys.exit(1)

    with open(json_path, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    print(f"[INFO] {len(articles)} articulos a procesar desde {json_path}")

    with app.app_context():
        # Resolver autor
        if args.author:
            author = User.query.get(args.author)
            if not author:
                print(f"[ERROR] user_id {args.author} no existe")
                sys.exit(1)
        else:
            author = User.query.filter_by(role='admin').first()
            if not author:
                print("[WARN] No hay ningun admin en BD; author_id quedara NULL")

        author_id = author.id if author else None
        print(f"[INFO] Autor: {author.name if author else 'NULL'} (id={author_id})")

        created = 0
        skipped = 0
        errors = 0

        for idx, art in enumerate(articles, 1):
            title = (art.get('title') or '').strip()
            body = (art.get('body') or '').strip()

            if not title or not body:
                print(f"  [{idx}] SKIP (sin titulo o body): {title[:60]}")
                errors += 1
                continue

            base_slug = slugify(title)
            # Verificar si ya existe uno con ese slug base O con ese titulo
            existing = KnowledgeArticle.query.filter(
                (KnowledgeArticle.slug == base_slug) |
                (KnowledgeArticle.title == title)
            ).first()

            if existing:
                print(f"  [{idx}] SKIP existe (id={existing.id}): {title[:70]}")
                skipped += 1
                continue

            if args.dry_run:
                print(f"  [{idx}] CREATE (dry): {title[:70]} [{art.get('category', '')}]")
                created += 1
                continue

            slug = unique_slug(base_slug)

            tags_raw = art.get('tags') or ''
            if isinstance(tags_raw, list):
                tags = ','.join([t.strip() for t in tags_raw if t.strip()])
            else:
                tags = tags_raw.strip()

            excerpt = (art.get('excerpt') or body[:280]).strip()[:300]
            category = (art.get('category') or '').strip()[:80] or None

            article = KnowledgeArticle(
                title=title[:200],
                slug=slug,
                body=body,
                excerpt=excerpt,
                category=category,
                tags=tags[:500],
                company=args.company,  # None = global
                author_id=author_id,
                is_published=True,
                is_public=False,
                version=1,
            )
            db.session.add(article)
            db.session.commit()
            print(f"  [{idx}] OK  id={article.id}  {title[:70]} [{category}]")
            created += 1

        print()
        print("=" * 60)
        print(f"RESUMEN: {created} creados, {skipped} saltados, {errors} errores")
        print("=" * 60)


if __name__ == '__main__':
    main()
