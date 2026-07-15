"""
seed_role_procesos.py

Crea el rol personalizado "PROCESOS" (base: technician, global a las 3 empresas).
Idempotente: si ya existe, actualiza los campos visuales sin duplicar.

Uso (Coolify terminal):
    python scripts/seed_role_procesos.py
"""
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import app, db, Config, log_audit


ROLE_KEY = 'procesos'
ROLE = {
    'key': ROLE_KEY,
    'label': 'PROCESOS',
    'base_role': 'technician',
    'color': '#0891b2',       # cian corporativo (distinto del azul técnico standard)
    'icon': '⚙️',
    'description': 'Especialistas del área de Procesos. Atienden tickets como parte del equipo TI (permisos de técnico).'
}


def run():
    with app.app_context():
        c = Config.query.filter_by(key='custom_roles').first()
        if c and c.value:
            try:
                roles = json.loads(c.value)
            except Exception:
                roles = []
        else:
            roles = []

        idx = next((i for i, r in enumerate(roles) if r.get('key') == ROLE_KEY), None)
        if idx is not None:
            # Actualizar en su lugar
            roles[idx] = ROLE
            action = 'actualizado'
        else:
            roles.append(ROLE)
            action = 'creado'

        payload = json.dumps(roles, ensure_ascii=False)
        if c:
            c.value = payload
        else:
            db.session.add(Config(key='custom_roles', value=payload))
        db.session.commit()

        try:
            log_audit('seed_custom_role', None, 'role', None,
                      f"Rol '{ROLE['label']}' {action} vía script de seed")
        except Exception:
            pass

        print(f"\n✅ Rol '{ROLE['label']}' {action}")
        print(f"   Clave:      {ROLE['key']}")
        print(f"   Rol base:   {ROLE['base_role']} (permisos de técnico)")
        print(f"   Ícono:      {ROLE['icon']}")
        print(f"   Color:      {ROLE['color']}")
        print(f"   Alcance:    Global (3 empresas)")
        print(f"\n   Total de roles personalizados en el sistema: {len(roles)}")
        print(f"\nPara asignarlo a un usuario:")
        print(f"  Panel admin → Configuración → Gestión de Usuarios → Editar usuario")
        print(f"  → seleccionar '{ROLE['label']}' en el desplegable Rol\n")


if __name__ == '__main__':
    run()
