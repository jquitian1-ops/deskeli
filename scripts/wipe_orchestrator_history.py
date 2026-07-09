"""
wipe_orchestrator_history.py — Borra el historial de acciones del Agent Orchestrator

Purga la tabla agent_actions. Solo se borra el HISTORIAL de decisiones —
no afecta tickets, subtareas, usuarios ni configuracion.

Uso desde Coolify terminal:
    python scripts/wipe_orchestrator_history.py                    # dry-run TODAS las empresas
    python scripts/wipe_orchestrator_history.py --confirm          # ejecuta wipe TODAS las empresas
    python scripts/wipe_orchestrator_history.py --company=pash --confirm  # solo una empresa
"""
import argparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import app, db, AgentAction


def run(company=None, dry_run=True):
    with app.app_context():
        q = AgentAction.query
        if company:
            q = q.filter(AgentAction.company == company)

        # Reporte pre-borrado
        total = q.count()
        by_agent = {}
        by_company = {}
        for a in q.with_entities(AgentAction.agent_name, AgentAction.company).all():
            by_agent[a.agent_name] = by_agent.get(a.agent_name, 0) + 1
            by_company[a.company] = by_company.get(a.company, 0) + 1

        target = company if company else 'TODAS las empresas'
        print(f'[wipe-orch] Filtro: {target}')
        print(f'[wipe-orch] Total AgentAction a borrar: {total}')
        if by_agent:
            print('[wipe-orch] Por agente:')
            for k, v in sorted(by_agent.items()):
                print(f'  - {k:12} {v}')
        if by_company and not company:
            print('[wipe-orch] Por empresa:')
            for k, v in sorted(by_company.items()):
                print(f'  - {k:12} {v}')

        if total == 0:
            print('[wipe-orch] Nada que borrar.')
            return

        if dry_run:
            print('\n[wipe-orch] DRY RUN — no se toco la BD. Corre con --confirm para ejecutar.')
            return

        # Ejecutar borrado
        deleted = q.delete(synchronize_session=False)
        db.session.commit()
        remaining = AgentAction.query.count() if not company else AgentAction.query.filter(AgentAction.company == company).count()
        print(f'\n[wipe-orch] ✅ Borrado. Filas eliminadas: {deleted}')
        print(f'[wipe-orch] AgentAction restantes ({"totales" if not company else company}): {remaining}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--company', type=str, default=None,
                        help='Codigo de empresa a filtrar (eliot/pash/primatela). Sin este flag borra TODAS.')
    parser.add_argument('--confirm', action='store_true',
                        help='Ejecuta el borrado real. Sin este flag, dry-run.')
    args = parser.parse_args()
    run(company=args.company, dry_run=not args.confirm)
