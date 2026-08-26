"""
seed_guiones_solicitud_usuario.py

Instala el guión "Solicitud Ingreso / Modificación de Usuario" en las 3
empresas (Eliot, Pash, Primatela) partiendo del template Primatela ya
diseñado (guion_solicitud_usuario_primatela.json).

Idempotente por code+company.

Uso (Coolify terminal):
    python scripts/seed_guiones_solicitud_usuario.py
"""
import json
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import app, db, Guion, GuionSubtask, User


ROOT = Path(__file__).resolve().parent
SOURCE_FILE = ROOT / 'guion_solicitud_usuario_primatela.json'

COMPANIES = {
    # code    (nombre bonito para el nombre del guión)
    'eliot': 'Manufacturas Eliot',
    'pash': 'Pash',
    'primatela': 'Primatela',
}


def _load_source():
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(f'Falta {SOURCE_FILE}')
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    guiones = data.get('guiones') or []
    if not guiones:
        raise ValueError('El JSON fuente no tiene "guiones".')
    return guiones[0]  # solo hay uno


def _adapt_text(text, source_name, target_name):
    """Reemplaza menciones de la empresa origen por la target en el texto."""
    if not text:
        return text
    return text.replace(source_name, target_name)


def _find_fallback_creator(company):
    u = User.query.filter_by(company=company, role='admin', is_active=True).first()
    if u:
        return u
    return User.query.filter_by(role='admin', is_active=True).first()


def run():
    src = _load_source()
    source_company_name = 'Primatela'
    print(f'[seed] Fuente: guión "{src["name"]}" ({len(src.get("subtasks") or [])} subtareas)')

    with app.app_context():
        created, updated = 0, 0

        for co_code, co_name in COMPANIES.items():
            creator = _find_fallback_creator(co_code)
            if not creator:
                print(f'[seed] ⚠  Sin admins en {co_code}, saltando.')
                continue

            code = f'solicitud-usuario-{co_code}'
            name = _adapt_text(src.get('name') or 'Solicitud Ingreso / Modificación de Usuario', source_company_name, co_name)
            description = _adapt_text(src.get('description') or '', source_company_name, co_name)

            existing = Guion.query.filter_by(code=code).first()
            if existing:
                existing.name = name[:200]
                existing.description = description
                existing.company = co_code
                existing.default_priority = src.get('default_priority') or 'medium'
                existing.default_category = src.get('default_category') or 'Accesos'
                existing.is_active = True
                # Borrar subtareas viejas para evitar drift
                GuionSubtask.query.filter_by(guion_id=existing.id).delete()
                db.session.flush()
                target_id = existing.id
                updated += 1
                print(f'[seed] Actualizado guión {code} (id={target_id})')
            else:
                g = Guion(
                    code=code,
                    name=name[:200],
                    description=description,
                    company=co_code,
                    default_priority=src.get('default_priority') or 'medium',
                    default_category=src.get('default_category') or 'Accesos',
                    is_active=True,
                    created_by_id=creator.id,
                )
                db.session.add(g)
                db.session.flush()
                target_id = g.id
                created += 1
                print(f'[seed] Creado guión {code} (id={target_id})')

            # Insertar subtareas adaptadas
            for st in src.get('subtasks') or []:
                db.session.add(GuionSubtask(
                    guion_id=target_id,
                    order_idx=int(st.get('order_idx') or 0),
                    title=_adapt_text(st.get('title') or '', source_company_name, co_name)[:200],
                    description=_adapt_text(st.get('description') or '', source_company_name, co_name),
                    category=st.get('category') or 'Accesos',
                    priority=st.get('priority') or 'medium',
                    assignee_id=None,  # el admin de cada empresa asignará técnicos después
                ))

        db.session.commit()
        print()
        print(f'[seed] ✅ Terminado. Creados: {created}, actualizados: {updated}')
        print()
        print('Recordá:')
        print('  • Los assignee_id quedan NULL — cada empresa debe asignar sus técnicos')
        print('    específicos desde el panel admin → Guiones.')
        print('  • Los pasos SAP mencionan RISE/FMS/AFS: en Eliot/Pash puede que apliquen')
        print('    distintos aplicativos. Revisá el guión de cada empresa y cerrá como N/A')
        print('    los pasos que no correspondan (o editá el JSON fuente si querés customizarlos).')


if __name__ == '__main__':
    run()
