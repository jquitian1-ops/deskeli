"""
seed_template_solicitud_usuario.py

Inserta la plantilla "Solicitud Ingreso/Modificación de Usuarios" en las 3
empresas (idempotente por name+company). Basada en el formato oficial de
Manufacturas Eliot / Pash / Primatela.

v2 (2026-07): agrega fecha_ingreso, remplazo, y soporta multiples accesos +
detalles SAP mediante textareas estructurados (una linea por item).

Uso (Coolify terminal):
    python scripts/seed_template_solicitud_usuario.py
"""
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import app, db, Template


TEMPLATE_NAME = 'Solicitud ingreso/modificación de usuarios'
TEMPLATE_DESC = 'Formato oficial para solicitar creación, modificación o eliminación de usuarios con sus accesos (SAP, redes, sistemas).'
TITLE_TEMPLATE = '[USUARIOS] [{{tipo_solicitud}}] {{nombre_tercero}} - {{cargo}}'
CATEGORY = 'Accesos'
PRIORITY = 'medium'

# Descripción prellenada: aparece como texto legible en el ticket
DESCRIPTION_TEMPLATE = """═══════════════════════════════════════════════════
SOLICITUD DE INGRESO / MODIFICACIÓN DE USUARIOS
═══════════════════════════════════════════════════

▶ I. INFORMACIÓN DE LA SOLICITUD

Tipo de Solicitud:        {{tipo_solicitud}}
Nombre del Tercero:       {{nombre_tercero}}
Documento:                {{documento}}
Cargo:                    {{cargo}}
Teléfono:                 {{telefono}}
Gerencia:                 {{gerencia}}
Jefe Inmediato:           {{jefe_inmediato}}
Centro de Costo:          {{centro_costo}}
Unidad de Negocio:        {{unidad_negocio}}
Ubicación:                {{ubicacion}}
Tipo de Contrato:         {{tipo_contrato}}
Fecha de Ingreso:         {{fecha_ingreso}}
¿Es reemplazo?:           {{remplazo}}
Usuario de Red actual:    {{usuario_red}}

▶ JUSTIFICACIÓN DE LOS ACCESOS

{{justificacion}}

▶ II. LISTA DE ACCESOS SOLICITADOS

Formato (uno por línea): NOMBRE | DESCRIPCIÓN | USUARIO ESPEJO | COSTO

{{accesos_lista}}

Total estimado: {{costo_total}}

▶ DETALLE SAP (si aplica)

Formato (uno por línea): VERSIÓN | AMBIENTE

{{sap_detalle}}

▶ APROBACIÓN

Jefe Inmediato:          {{aprobador_jefe}}
Área Solicitante:        {{aprobador_area}}
"""


FORM_FIELDS = [
    # ── I. INFORMACIÓN DE LA SOLICITUD ──────────────────────────
    {
        'name': 'tipo_solicitud',
        'label': '📋 Tipo de solicitud',
        'type': 'select',
        'required': True,
        'options': ['INGRESO', 'MODIFICACIÓN', 'ELIMINACIÓN']
    },
    {
        'name': 'nombre_tercero',
        'label': '👤 Nombre completo del usuario',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: ROSARIO MARISCAL'
    },
    {
        'name': 'documento',
        'label': '🪪 Documento de identidad',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: 3852273'
    },
    {
        'name': 'cargo',
        'label': '💼 Cargo',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: LIDER DE TIENDA'
    },
    {
        'name': 'telefono',
        'label': '📞 Teléfono / celular de contacto',
        'type': 'text',
        'required': False,
        'placeholder': 'Ej: +59177631301 (incluir código país si es internacional)'
    },
    {
        'name': 'gerencia',
        'label': '🏢 Gerencia',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: COMERCIAL TEKS, FINANCIERA, OPERACIONES'
    },
    {
        'name': 'jefe_inmediato',
        'label': '👔 Jefe inmediato',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: GRACIELA FLOREZ CORDERO'
    },
    {
        'name': 'centro_costo',
        'label': '💰 Centro de costo / División',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: 21700001151800000002 - GERENCIA VENTAS PORTOFINO'
    },
    {
        'name': 'unidad_negocio',
        'label': '🏭 Unidad de negocio',
        'type': 'select',
        'required': True,
        'options': ['MANUFACTURAS ELIOT', 'PASH', 'PRIMATELA']
    },
    {
        'name': 'ubicacion',
        'label': '📍 Ubicación / sede / país',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: ELIOT CALLE 19 · PASH CENTRO · PANAMA U OTROS PAISES · BOLIVIA'
    },
    {
        'name': 'tipo_contrato',
        'label': '📄 Tipo de contrato',
        'type': 'select',
        'required': True,
        'options': ['FIJO', 'TEMPORAL', 'CONTRATISTA', 'PRÁCTICAS', 'OTRO']
    },
    {
        'name': 'fecha_ingreso',
        'label': '📅 Fecha de ingreso',
        'type': 'date',
        'required': True,
        'placeholder': 'AAAA-MM-DD'
    },
    {
        'name': 'remplazo',
        'label': '🔁 ¿Es reemplazo de otro colaborador?',
        'type': 'select',
        'required': True,
        'options': ['NO', 'SÍ']
    },
    {
        'name': 'usuario_red',
        'label': '🔑 Usuario de red actual (si existe)',
        'type': 'text',
        'required': False,
        'placeholder': 'Ej: rmariscal (0 o vacío si es nuevo)'
    },
    {
        'name': 'justificacion',
        'label': '📝 Justificación de los accesos',
        'type': 'textarea',
        'required': True,
        'placeholder': 'Ej: Se solicitan equipos para Rosario Mariscal en Bolivia.'
    },

    # ── II. LISTA DE ACCESOS ────────────────────────────────────
    # Un textarea estructurado para listar cualquier cantidad de accesos.
    # Formato por linea: NOMBRE | DESCRIPCIÓN | USUARIO ESPEJO | COSTO
    {
        'name': 'accesos_lista',
        'label': '🎯 Lista de accesos solicitados (uno por línea)',
        'type': 'textarea',
        'required': True,
        'placeholder': (
            'Formato: NOMBRE | DESCRIPCIÓN | USUARIO ESPEJO | COSTO\n\n'
            'Ejemplo:\n'
            'ELEMENTOS DE TECNOLOGIA | MOUSE USB, PORTATIL CI7/16GB/500GB SSD | N/A | -\n'
            'HERRAMIENTAS OFIMÁTICAS | LICENCIA OFFICE 365 E3 TEAMS | N/A | 140\n'
            'CREACION VPN | DAR ACCESO A VPN | N/A | -\n'
            'ULTRASYSTEM | CREAR USUARIOS CON PERMISOS DE TIENDAS PARA BOLIVIA | TIENDA | -\n'
            'SAP PASH | N/A | TIENDA PAISES | -\n'
            'SAP | CREAR SAP RISE Y SAP PAISES | TIENDA PAISES | 1300'
        )
    },
    {
        'name': 'costo_total',
        'label': '💵 Costo total estimado (suma)',
        'type': 'text',
        'required': False,
        'placeholder': 'Ej: 1440'
    },

    # ── DETALLE SAP (opcional, uno por línea) ───────────────────
    {
        'name': 'sap_detalle',
        'label': '🔧 Detalle SAP (uno por línea: VERSIÓN | AMBIENTE)',
        'type': 'textarea',
        'required': False,
        'placeholder': (
            'Dejar vacío si no aplica.\n\n'
            'Formato: VERSIÓN | AMBIENTE\n\n'
            'Ejemplo:\n'
            'RISE | PRODUCTIVO\n'
            'FMS PAISES | PRODUCTIVO'
        )
    },

    # ── APROBACIÓN ──────────────────────────────────────────────
    {
        'name': 'aprobador_jefe',
        'label': '✅ Jefe inmediato que aprueba',
        'type': 'text',
        'required': True,
        'placeholder': 'Nombre completo (ej: GRACIELA FLOREZ CORDERO)'
    },
    {
        'name': 'aprobador_area',
        'label': '✅ Responsable del área solicitante',
        'type': 'text',
        'required': True,
        'placeholder': 'Nombre completo (ej: GRACIELA FLOREZ CORDERO)'
    },
]


def run():
    with app.app_context():
        companies = ['eliot', 'pash', 'primatela']
        ff_json = json.dumps(FORM_FIELDS, ensure_ascii=False)

        created, updated = 0, 0
        for co in companies:
            existing = Template.query.filter_by(name=TEMPLATE_NAME, company=co).first()
            if existing:
                existing.description = TEMPLATE_DESC
                existing.title_template = TITLE_TEMPLATE
                existing.description_template = DESCRIPTION_TEMPLATE
                existing.category = CATEGORY
                existing.priority = PRIORITY
                existing.form_fields = ff_json
                updated += 1
                print(f'[seed] Actualizada plantilla para {co}')
            else:
                t = Template(
                    name=TEMPLATE_NAME,
                    description=TEMPLATE_DESC,
                    title_template=TITLE_TEMPLATE,
                    description_template=DESCRIPTION_TEMPLATE,
                    category=CATEGORY,
                    priority=PRIORITY,
                    company=co,
                    is_system=True,
                    form_fields=ff_json,
                )
                db.session.add(t)
                created += 1
                print(f'[seed] Creada plantilla para {co}')

        db.session.commit()
        print(f'\n[seed] ✅ Terminado. Creadas: {created}, actualizadas: {updated}')
        print(f'[seed] Total campos en el formulario: {len(FORM_FIELDS)}')


if __name__ == '__main__':
    run()
