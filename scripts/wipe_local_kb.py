"""Borra TODOS los articulos de knowledge_articles en la BD local.
Uso solo para limpiar el local antes de que Coolify auto-siembre en produccion.

NO ejecutar contra produccion.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import app, db, KnowledgeArticle, KnowledgeArticleFeedback

with app.app_context():
    fb = KnowledgeArticleFeedback.query.delete()
    n = KnowledgeArticle.query.delete()
    db.session.commit()
    print(f"[OK] Borrados {n} articulos y {fb} feedback de la KB local.")
