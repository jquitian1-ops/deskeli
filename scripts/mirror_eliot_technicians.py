"""
mirror_eliot_technicians.py — Backfill: duplicar tecnicos Eliot en Pash/Primatela

Corre despues de agregar el mirroring automatico para "poner al dia" los
tecnicos que ya existian en Eliot antes de la feature.

Uso desde Coolify terminal:
    python scripts/mirror_eliot_technicians.py           # dry-run
    python scripts/mirror_eliot_technicians.py --confirm # ejecuta el mirror
"""
import argparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import (
    app, db, User,
    mirror_technician_to_other_companies,
    MIRROR_SOURCE_COMPANY, MIRROR_TARGET_COMPANIES,
)


def run(dry_run=False):
    with app.app_context():
        eliot_techs = User.query.filter_by(
            company=MIRROR_SOURCE_COMPANY,
            role='technician'
        ).all()

        print(f'[mirror] Tecnicos en {MIRROR_SOURCE_COMPANY}: {len(eliot_techs)}')
        if not eliot_techs:
            print('[mirror] Nada que hacer.')
            return

        actions = []
        for t in eliot_techs:
            for target in MIRROR_TARGET_COMPANIES:
                existing_mirror = User.query.filter_by(
                    mirrored_from_id=t.id,
                    company=target
                ).first()
                if existing_mirror:
                    actions.append(('update', target, t.username, existing_mirror.id))
                    continue
                # Chequear colisión con usuario local
                conflict = User.query.filter(
                    User.company == target,
                    db.or_(
                        User.username == t.username,
                        db.func.lower(User.email) == (t.email or '').lower()
                    )
                ).first()
                if conflict:
                    actions.append(('skip', target, t.username, f'conflicto con user id={conflict.id}'))
                    continue
                actions.append(('create', target, t.username, None))

        # Reporte
        creates = sum(1 for a in actions if a[0] == 'create')
        updates = sum(1 for a in actions if a[0] == 'update')
        skips = sum(1 for a in actions if a[0] == 'skip')
        print(f'[mirror] Plan:  create={creates}  update={updates}  skip={skips}')
        for a in actions:
            print(f'  [{a[0]:>6}] {a[2]:20}  → {a[1]:10}  {a[3] or ""}')

        if dry_run:
            print('\n[mirror] DRY RUN — no se toco la BD. Corre con --confirm para aplicar.')
            return

        # Ejecutar
        total = 0
        for t in eliot_techs:
            total += mirror_technician_to_other_companies(t)
        db.session.commit()
        print(f'\n[mirror] ✅ Terminado. Filas afectadas: {total}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--confirm', action='store_true',
                        help='Ejecuta el mirror real. Sin este flag, dry-run.')
    args = parser.parse_args()
    run(dry_run=not args.confirm)
