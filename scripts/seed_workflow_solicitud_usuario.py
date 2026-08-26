"""
seed_workflow_solicitud_usuario.py

Instala en las 3 empresas (Eliot, Pash, Primatela) el ApprovalWorkflow que
dispara para la plantilla "Creación y Modificación de Usuarios" con
aprobadores mixtos (dinámicos + condicionales):

    Paso 1  →  Jefe Inmediato        (dinámico, campo del form: jefe_inmediato)
    Paso 2  →  Responsable del Área  (dinámico, campo del form: responsable_area)
    Paso 3  →  Gerente de Tecnología (estático por empresa, CONDICIONAL:
               solo si el empleado marca el control ELEMENTOS DE TECNOLOGÍA)

Este 3er nivel solo se activa cuando la solicitud incluye pedido de equipos
(portátil, monitor, teclado, etc). En ese caso el ticket queda en
pending_approval hasta que los 3 aprobadores aprueben.

Idempotente: si ya existe un workflow con el mismo name+company, lo actualiza.

Configuración:
  - Editá `IT_MANAGER_EMAIL_BY_COMPANY` abajo con los emails reales del
    Gerente de TI de cada empresa. Si el email no matchea (o queda None),
    se usa como fallback el primer admin activo de la empresa (con warning).
  - El admin puede reconfigurar quién es el Gerente de TI después desde el
    UI de /admin/approvals (editar el workflow, paso 3).

Uso (Coolify terminal):
    python scripts/seed_workflow_solicitud_usuario.py
"""
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import app, db, ApprovalWorkflow, User


WORKFLOW_NAME = 'Aprobación · Creación y Modificación de Usuarios'
WORKFLOW_DESC = (
    'Workflow que dispara automáticamente cuando un empleado crea un ticket '
    'con la plantilla "Creación y Modificación de Usuarios". Requiere '
    'aprobación en hasta 3 pasos: (1) el jefe inmediato seleccionado en el '
    'form, (2) el responsable del área seleccionado en el form, y (3) — solo '
    'si la solicitud incluye ELEMENTOS DE TECNOLOGÍA — el Gerente de '
    'Tecnología de la empresa. Solo cuando todos los aprobadores aplicables '
    'aprueban, el ticket pasa a la cola de operación y TI ejecuta los '
    'controles marcados.'
)
TRIGGER_TEMPLATE_NAME = 'Creación y Modificación de Usuarios'
TRIGGER_CATEGORY = 'Accesos'


# ═════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN: emails del Gerente de TI por empresa
# ═════════════════════════════════════════════════════════════════════════════
# Reemplazá con los emails reales. Si el email no existe en la BD (o queda
# None), el script cae al fallback: primer admin activo de esa empresa.
# También podés reconfigurarlo después desde /admin/approvals (editar
# workflow → paso 3 → cambiar user_id).
IT_MANAGER_EMAIL_BY_COMPANY = {
    'eliot': None,      # ej: 'fernando.ramirez@eliot.com'
    'pash': None,       # ej: 'gerente.ti@pash.com.co'
    'primatela': None,  # ej: 'gerente.ti@primatela.com'
}


def _find_it_manager(company):
    """Busca al Gerente de TI de la empresa. Devuelve User o None."""
    email = IT_MANAGER_EMAIL_BY_COMPANY.get(company)
    if email:
        u = User.query.filter(
            db.func.lower(User.email) == email.lower(),
            User.company == company,
            User.is_active == True,
        ).first()
        if u:
            return u
        print(f'[seed] [warn]  Email "{email}" para Gerente TI de {company} no matcheó ningún usuario activo. Usando fallback.')
    # Fallback: primer admin activo de la empresa
    fallback = User.query.filter_by(company=company, role='admin', is_active=True).first()
    if fallback:
        print(f'[seed] [warn]  Fallback en {company}: usando "{fallback.name}" (id={fallback.id}) como Gerente TI. Ajustar desde UI si corresponde.')
    return fallback


def _find_fallback_admin(company):
    """Para created_by_id del workflow."""
    u = User.query.filter_by(company=company, role='admin', is_active=True).first()
    if u:
        return u
    return User.query.filter_by(role='admin', is_active=True).first()


def _build_approvers_for(company):
    """Arma la lista de aprobadores para una empresa específica."""
    approvers = [
        {
            'order': 1,
            'role_label': 'Jefe Inmediato (según form)',
            'user_from_form_field': 'jefe_inmediato',
        },
        {
            'order': 2,
            'role_label': 'Responsable del Área (según form)',
            'user_from_form_field': 'responsable_area',
        },
    ]
    # 3er paso condicional: Gerente de TI, solo si marcaron ELEMENTOS DE TECNOLOGÍA
    it_manager = _find_it_manager(company)
    if it_manager:
        approvers.append({
            'order': 3,
            'role_label': 'Gerente de Tecnología (por elementos tecnológicos)',
            'user_id': it_manager.id,
            'condition_control_marked': 'elementos_tecnologia',
        })
    else:
        print(f'[seed] [warn]  Sin Gerente TI ni fallback en {company}. Solo 2 aprobadores en este workflow.')
    return approvers


def run():
    with app.app_context():
        companies = ['eliot', 'pash', 'primatela']
        created, updated = 0, 0

        for co in companies:
            admin = _find_fallback_admin(co)
            if not admin:
                print(f'[seed] [warn]  Sin admins en {co}, saltando (crear un admin primero).')
                continue

            approvers = _build_approvers_for(co)
            approvers_json = json.dumps(approvers, ensure_ascii=False)

            existing = ApprovalWorkflow.query.filter_by(
                name=WORKFLOW_NAME, company=co
            ).first()

            if existing:
                existing.description = WORKFLOW_DESC
                existing.trigger_category = TRIGGER_CATEGORY
                existing.trigger_priority = None
                existing.trigger_template_name = TRIGGER_TEMPLATE_NAME
                existing.approvers_json = approvers_json
                existing.is_active = True
                updated += 1
                print(f'[seed] Actualizado workflow para {co} (id={existing.id}, {len(approvers)} pasos)')
            else:
                w = ApprovalWorkflow(
                    company=co,
                    name=WORKFLOW_NAME,
                    description=WORKFLOW_DESC,
                    trigger_category=TRIGGER_CATEGORY,
                    trigger_priority=None,
                    trigger_template_name=TRIGGER_TEMPLATE_NAME,
                    approvers_json=approvers_json,
                    is_active=True,
                    created_by_id=admin.id,
                )
                db.session.add(w)
                db.session.flush()
                created += 1
                print(f'[seed] Creado workflow para {co} (id={w.id}, {len(approvers)} pasos)')

        db.session.commit()
        print()
        print(f'[seed] ✅ Terminado. Creados: {created}, actualizados: {updated}')
        print()
        print('Trigger:')
        print(f'  categoria = "{TRIGGER_CATEGORY}"')
        print(f'  plantilla = "{TRIGGER_TEMPLATE_NAME}"')
        print()
        print('Aprobadores:')
        print('  1. Jefe Inmediato          ⚡ Dinámico (campo: "jefe_inmediato")')
        print('  2. Responsable del Área    ⚡ Dinámico (campo: "responsable_area")')
        print('  3. Gerente de Tecnología   🎯 Estático · CONDICIONAL')
        print('     └─ solo activo si empleado marca control "elementos_tecnologia"')
        print()
        print('Notas:')
        print('  • Si la solicitud NO pide elementos de tecnología, solo se ejecutan')
        print('    los pasos 1 y 2 (el paso 3 se salta y se registra en audit log).')
        print('  • Si SÍ los pide, los 3 aprobadores deben aprobar secuencialmente.')
        print('  • Ajustá IT_MANAGER_EMAIL_BY_COMPANY con los emails reales del')
        print('    Gerente de TI, o reconfigurá el user_id del paso 3 desde el UI')
        print('    (/admin/approvals → editar workflow).')


if __name__ == '__main__':
    run()
