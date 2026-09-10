"""
seed_approval_flow_demo.py

Instala el ApprovalFlow "Sistemas" en la empresa Pash para la demostración,
con 4 aprobadores secuenciales:

    Paso 1 → cat@patprimo.com.co          (Analista IT)
    Paso 2 → clopez@patprimo.com.co       (Jefe de área)
    Paso 3 → mesadeayuda@patprimo.com.co  (Gerente de área)
    Paso 4 → nlucumi@patprimo.com.co      (Gerente de Servicios IT)

El ticket padre generado tras la aprobación del último se asigna a:
    ticket_assignee_email = cat@patprimo.com.co

Idempotente: si ya existe un flujo (company="pash", area="Sistemas") lo
actualiza; si no, lo crea.

Uso:
    python scripts/seed_approval_flow_demo.py
"""
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import app, db, ApprovalFlow


COMPANY = 'pash'
AREA = 'Sistemas'
STEPS = [
    {'email': 'cat@patprimo.com.co',          'label': 'Analista IT'},
    {'email': 'clopez@patprimo.com.co',       'label': 'Jefe de área'},
    {'email': 'mesadeayuda@patprimo.com.co',  'label': 'Gerente de área'},
    {'email': 'nlucumi@patprimo.com.co',      'label': 'Gerente de Servicios IT'},
]
TICKET_ASSIGNEE = 'cat@patprimo.com.co'
DESCRIPTION = 'Flujo demo para el área de Sistemas: 4 aprobaciones secuenciales por correo.'


def run():
    with app.app_context():
        existing = ApprovalFlow.query.filter_by(company=COMPANY, area=AREA).first()
        steps_json = json.dumps(STEPS, ensure_ascii=False)
        if existing:
            existing.description = DESCRIPTION
            existing.steps_json = steps_json
            existing.ticket_assignee_email = TICKET_ASSIGNEE
            existing.is_active = True
            db.session.commit()
            print(f'[seed] Flujo actualizado (id={existing.id})')
        else:
            f = ApprovalFlow(
                company=COMPANY,
                area=AREA,
                description=DESCRIPTION,
                steps_json=steps_json,
                ticket_assignee_email=TICKET_ASSIGNEE,
                is_active=True,
            )
            db.session.add(f)
            db.session.commit()
            print(f'[seed] Flujo creado (id={f.id})')

        print()
        print(f'Empresa:   {COMPANY}')
        print(f'Area:      {AREA}')
        print(f'Ticket -> {TICKET_ASSIGNEE}')
        print()
        print('Pasos:')
        for i, s in enumerate(STEPS, start=1):
            print(f'  {i}. {s["label"]:30s} -> {s["email"]}')
        print()
        print('Listo. En /solicitudes-usuarios/nueva, elegi el area "Sistemas"')
        print('para que la solicitud use este flujo.')


if __name__ == '__main__':
    run()
