"""
seed_template_solicitud_usuario.py

Inserta la plantilla "Solicitud Ingreso/Modificación de Usuarios" en las 3
empresas (idempotente por name+company). Basada en el formato oficial de
Manufactureras Eliot / Pash / Primatela.

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
Usuario de Red (si tiene): {{usuario_red}}

▶ JUSTIFICACIÓN DE LOS ACCESOS

{{justificacion}}

▶ II. LISTA DE ACCESOS SOLICITADOS

Nombre del acceso:       {{acceso_nombre}}
Descripción:             {{acceso_descripcion}}
Usuario espejo:          {{usuario_espejo}}
Costo estimado:          {{costo}}

▶ DETALLE SAP (si aplica)

Versión:                 {{sap_version}}
Ambiente:                {{sap_ambiente}}

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
        'placeholder': 'Ej: JENNY ALEJANDRA ROA QUEVEDO'
    },
    {
        'name': 'documento',
        'label': '🪪 Documento de identidad',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: 1030701080'
    },
    {
        'name': 'cargo',
        'label': '💼 Cargo',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: Analista Planeación Financiera'
    },
    {
        'name': 'telefono',
        'label': '📞 Teléfono / celular de contacto',
        'type': 'text',
        'required': False,
        'placeholder': 'Ej: 3133520058'
    },
    {
        'name': 'gerencia',
        'label': '🏢 Gerencia',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: FINANCIERA, COMERCIAL, OPERACIONES'
    },
    {
        'name': 'jefe_inmediato',
        'label': '👔 Jefe inmediato',
        'type': 'text',
        'required': True,
        'placeholder': 'Nombre completo del jefe inmediato'
    },
    {
        'name': 'centro_costo',
        'label': '💰 Centro de costo / División',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: 1030900310301000102 - PLANEACIÓN FINANCIERA'
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
        'label': '📍 Ubicación / sede',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: ELIOT CALLE 19, PASH CENTRO, PRIMATELA NORTE'
    },
    {
        'name': 'tipo_contrato',
        'label': '📄 Tipo de contrato',
        'type': 'select',
        'required': True,
        'options': ['FIJO', 'TEMPORAL', 'CONTRATISTA', 'PRÁCTICAS', 'OTRO']
    },
    {
        'name': 'usuario_red',
        'label': '🔑 Usuario de red actual (si existe)',
        'type': 'text',
        'required': False,
        'placeholder': 'Ej: yroa (dejar vacío si es nuevo)'
    },
    {
        'name': 'justificacion',
        'label': '📝 Justificación de los accesos',
        'type': 'textarea',
        'required': True,
        'placeholder': 'Ej: Solicito acceso a FMS PAISES en SAP para gestión financiera del mercado internacional'
    },

    # ── II. LISTA DE ACCESOS ────────────────────────────────────
    {
        'name': 'acceso_nombre',
        'label': '🎯 Nombre del acceso solicitado',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: SAP, VPN, Correo, SharePoint, ERP'
    },
    {
        'name': 'acceso_descripcion',
        'label': '📃 Descripción detallada del acceso',
        'type': 'textarea',
        'required': True,
        'placeholder': 'Ej: Solicito acceso a FMS PAISES en SAP, no cuento con usuarios tengo usuario de RISE'
    },
    {
        'name': 'usuario_espejo',
        'label': '👥 Usuario espejo (perfil a copiar)',
        'type': 'text',
        'required': False,
        'placeholder': 'Ej: Mlopez (opcional)'
    },
    {
        'name': 'costo',
        'label': '💵 Costo estimado (si aplica)',
        'type': 'text',
        'required': False,
        'placeholder': 'Ej: 1300'
    },

    # ── DETALLE SAP (opcional) ──────────────────────────────────
    {
        'name': 'sap_version',
        'label': '🔧 Versión SAP (si aplica)',
        'type': 'text',
        'required': False,
        'placeholder': 'Ej: FMS PAISES, S/4HANA, ECC 6.0'
    },
    {
        'name': 'sap_ambiente',
        'label': '🌐 Ambiente SAP',
        'type': 'select',
        'required': False,
        'options': ['NO APLICA', 'PRODUCTIVO', 'CALIDAD', 'DESARROLLO', 'TODOS']
    },

    # ── APROBACIÓN ──────────────────────────────────────────────
    {
        'name': 'aprobador_jefe',
        'label': '✅ Jefe inmediato que aprueba',
        'type': 'text',
        'required': True,
        'placeholder': 'Nombre completo (ej: MARGARITA MARIA SALAZAR HUERTAS)'
    },
    {
        'name': 'aprobador_area',
        'label': '✅ Responsable del área solicitante',
        'type': 'text',
        'required': True,
        'placeholder': 'Nombre completo (ej: CRISTIAN GEOVANNY MOLINA ALEAGA)'
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
                # Actualizar contenido (permite iterar sobre el diseño)
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
