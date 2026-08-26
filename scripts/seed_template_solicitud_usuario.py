"""
seed_template_solicitud_usuario.py

Instala en las 3 empresas (Eliot, Pash, Primatela) la plantilla
"Creación y Modificación de Usuarios" basada en el formulario oficial
del sistema T-APPS de Manufacturas Eliot.

Estructura:
- 14 campos generales (Tipo de Solicitud, Unidad de Negocio, Documento,
  Nombre, Cargo, Ubicación, Fecha Ingreso, División/CC, Jefe Inmediato,
  Gerencia, Tipo de Contrato, Reemplazo, Justificación).
- Adjuntos: 1 archivo opcional.
- 24 controles (tipo control_list): usuario marca cuáles necesita y
  completa descripción + Usuario Espejo cuando aplique.

Aprobación: 2 niveles dinámicos (jefe_inmediato + responsable_area) —
resueltos por el motor de workflow en tiempo de creación del ticket.

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


TEMPLATE_NAME = 'Creación y Modificación de Usuarios'
TEMPLATE_DESC = (
    'Formato oficial para solicitar el ingreso, modificación o traslado de '
    'usuarios y sus accesos (Directorio Activo, correo, VPN, permisos, '
    'aplicativos textiles, comerciales, SAP y KACTUS). Basada en el '
    'formulario T-APPS del sistema origen. Pasa por 2 niveles de aprobación: '
    'jefe inmediato + responsable del área.'
)
TITLE_TEMPLATE = '[USUARIOS] [{{tipo_solicitud}}] {{nombre}} - {{cargo}}'
CATEGORY = 'Accesos'
PRIORITY = 'medium'


# ═════════════════════════════════════════════════════════════════════════════
# Los 24 controles del formulario T-APPS
# Cada control:
#   code           id único (se usa como clave en el JSON de respuesta)
#   name           nombre visible en la tabla
#   detalle        texto fijo del "Detalle del Control" tal como en T-APPS
#   type           'textarea' (por defecto) o 'dropdown'
#   needs_espejo   True si requiere campo "Usuario Espejo" adicional
#   options        [] si es dropdown, las opciones
# ═════════════════════════════════════════════════════════════════════════════
CONTROLES = [
    # ── Equipos y ofimática ──
    {
        'code': 'elementos_tecnologia',
        'name': 'ELEMENTOS DE TECNOLOGÍA',
        'detalle': 'Seleccione los elementos de tecnología que requiera solicitar, esto está sujeto a posterior aprobación de las gerencias de área por costos.',
        'type': 'textarea',
        'needs_espejo': False,
    },
    {
        'code': 'herramientas_ofimaticas',
        'name': 'HERRAMIENTAS OFIMÁTICAS',
        'detalle': 'Herramientas ofimáticas (seleccione los aplicativos a los cuales requiere acceso y justificación).',
        'type': 'textarea',
        'needs_espejo': False,
    },
    # ── Red / correo / VPN / carpetas ──
    {
        'code': 'directorio_activo',
        'name': 'DIRECTORIO ACTIVO',
        'detalle': 'Usuario para ingresar al equipo de cómputo.',
        'type': 'textarea',
        'needs_espejo': False,
    },
    {
        'code': 'correo_corporativo',
        'name': 'CORREO ELECTRÓNICO CORPORATIVO',
        'detalle': 'Dirección de correo electrónico corporativo (indicar el dominio. Ejemplo: @tekstelas.com; @patprimo.com.co; @pash.com.co; @patprimo.co; etc. Adicional indicar justificación y tipo de licencia: solo correo, básica o estándar).',
        'type': 'textarea',
        'needs_espejo': False,
    },
    {
        'code': 'creacion_vpn',
        'name': 'CREACIÓN VPN',
        'detalle': 'Se requiere para conexión a los aplicativos en modalidad teletrabajo.',
        'type': 'textarea',
        'needs_espejo': False,
    },
    {
        'code': 'carpetas_compartidas',
        'name': 'CARPETAS COMPARTIDAS',
        'detalle': 'Carpetas compartidas (por favor indicar la ruta de la carpeta donde requiere el acceso).',
        'type': 'textarea',
        'needs_espejo': False,
    },
    # ── Permisos ──
    {
        'code': 'permiso_imprimir',
        'name': 'PERMISO DE IMPRIMIR',
        'detalle': 'Permisos de impresión (B/N; para opción de color está sujeto a aprobación por Dirección Operaciones e Infraestructura).',
        'type': 'textarea',
        'needs_espejo': False,
    },
    {
        'code': 'permisos_internet',
        'name': 'PERMISOS DE INTERNET',
        'detalle': 'Debe detallar las páginas a las cuales van a acceder y especificar la categoría que requiere: AVANZADO (VIP) aplica si requiere redes sociales, permite un acceso más amplio con restricciones mínimas; BÁSICO (STAFF) ofrece un nivel básico de acceso con filtros más restrictivos.',
        'type': 'textarea',
        'needs_espejo': False,
    },
    {
        'code': 'puntos_electricos_red',
        'name': 'PUNTOS ELÉCTRICOS O RED',
        'detalle': 'Describa si es revisión o nuevos. Adicional las cantidades de puntos de red y/o eléctricos que se requiere si son puntos nuevos.',
        'type': 'textarea',
        'needs_espejo': False,
    },
    {
        'code': 'sql_gerber',
        'name': 'SQL GERBER',
        'detalle': 'Permisos SQL Gerber, se debe informar el nombre de la carpeta y el tipo de permiso (lectura, escritura o lectura/escritura).',
        'type': 'textarea',
        'needs_espejo': False,
    },
    {
        'code': 'puertos_usb',
        'name': 'PUERTOS USB',
        'detalle': 'Habilitación de puertos USB (deben justificar por qué se requiere el acceso). Requiere adjuntar Hoja 4 firmada por el usuario.',
        'type': 'textarea',
        'needs_espejo': False,
    },
    # ── Aplicativos textiles (todos con Usuario Espejo) ──
    {
        'code': 'externos_confeccion',
        'name': 'EXTERNOS CONFECCIÓN',
        'detalle': 'Usuario para ingreso al aplicativo Externos Confección. Debe indicar en su respectivo campo el usuario espejo, este debe estar activo en la compañía.',
        'type': 'textarea',
        'needs_espejo': True,
    },
    {
        'code': 'eliotconf',
        'name': 'ELIOTCONF',
        'detalle': 'Usuario para ingreso al aplicativo Eliotconf. Debe indicar en su respectivo campo el usuario espejo, este debe estar activo en la compañía.',
        'type': 'textarea',
        'needs_espejo': True,
    },
    {
        'code': 'eliotex',
        'name': 'ELIOTEX',
        'detalle': 'Usuario para ingreso al aplicativo Eliotex. Debe indicar en su respectivo campo el usuario espejo, este debe estar activo en la compañía.',
        'type': 'textarea',
        'needs_espejo': True,
    },
    {
        'code': 'acatex',
        'name': 'ACATEX',
        'detalle': 'Usuario para ingreso al aplicativo Acatex. Debe indicar en su respectivo campo el usuario espejo, este debe estar activo en la compañía.',
        'type': 'textarea',
        'needs_espejo': True,
    },
    {
        'code': 'costotex',
        'name': 'COSTOTEX',
        'detalle': 'Usuario para ingreso al aplicativo Costotex. Debe indicar en su respectivo campo el usuario espejo, este debe estar activo en la compañía.',
        'type': 'textarea',
        'needs_espejo': True,
    },
    {
        'code': 'vertex',
        'name': 'VERTEX',
        'detalle': 'Usuario para ingreso al aplicativo Vertex. Debe indicar en su respectivo campo el usuario espejo, este debe estar activo en la compañía.',
        'type': 'textarea',
        'needs_espejo': True,
    },
    {
        'code': 'tejido_plano',
        'name': 'TEJIDO PLANO',
        'detalle': 'Usuario para ingreso al aplicativo Tejido Plano. Debe indicar en su respectivo campo el usuario espejo, este debe estar activo en la compañía.',
        'type': 'textarea',
        'needs_espejo': True,
    },
    # ── Comercial / retail ──
    {
        'code': 'retail',
        'name': 'RETAIL',
        'detalle': 'Usuario para ingreso al aplicativo Retail. Debe indicar el usuario espejo (activo en la compañía) y especificar para qué país y marcas requiere los accesos.',
        'type': 'textarea',
        'needs_espejo': True,
    },
    {
        'code': 'skycm',
        'name': 'SKYCM',
        'detalle': 'Solicitud al aplicativo Skycm Market Place (asesores comerciales).',
        'type': 'textarea',
        'needs_espejo': False,
    },
    {
        'code': 'biotime',
        'name': 'BIOTIME',
        'detalle': 'Biotime: indicar el país y usuario espejo donde requiere el acceso.',
        'type': 'textarea',
        'needs_espejo': False,
    },
    # ── SAP y KACTUS ──
    {
        'code': 'kactus',
        'name': 'KACTUS',
        'detalle': 'Plataforma de acceso a módulos de nómina y gestión humana a nivel de creación de usuarios, permisos, accesos a programas, roles y tipo de usuario.',
        'type': 'textarea',
        'needs_espejo': True,
    },
    {
        'code': 'sap_pash',
        'name': 'SAP PASH',
        'detalle': 'Solo seleccionar cuando sea tipo de solicitud MODIFICACIÓN y ya cuente con usuario en el aplicativo SAP Pash.',
        'type': 'textarea',
        'needs_espejo': True,
    },
    {
        'code': 'sap',
        'name': 'SAP',
        'detalle': 'En el campo descripción indicar si ya cuenta con usuario, adicional deben indicar el usuario espejo y el ambiente (PRODUCTIVO, PREPRODUCTIVO, CALIDAD, DESARROLLO), indicar versión (AFS, FMS PASH, FMS PAISES, EWM, RISE).',
        'type': 'textarea',
        'needs_espejo': True,
    },
]


# ═════════════════════════════════════════════════════════════════════════════
# Descripción prellenada: se genera automáticamente con los valores del form.
# {{controles_texto}} lo compone el frontend con los controles marcados.
# ═════════════════════════════════════════════════════════════════════════════
DESCRIPTION_TEMPLATE = """═══════════════════════════════════════════════════
CREACIÓN Y MODIFICACIÓN DE USUARIOS
═══════════════════════════════════════════════════

▶ I. DATOS GENERALES

Tipo de Solicitud:        {{tipo_solicitud}}
Unidad de Negocio:        {{unidad_negocio}}
Documento:                {{documento}}
Nombre:                   {{nombre}}
Cargo:                    {{cargo}}
Número de Contacto:       {{numero_contacto}}
Ubicación:                {{ubicacion}}
Fecha de Ingreso:         {{fecha_ingreso}}
División/Centro de Costo: {{division_centro_costo}}
Jefe Inmediato:           {{jefe_inmediato}}
Gerencia / Área:          {{gerencia_area}}
Tipo de Contrato:         {{tipo_contrato}}
¿Es reemplazo?:           {{reemplazo}}

▶ II. JUSTIFICACIÓN DE LOS ACCESOS

{{justificacion}}

▶ III. CONTROLES SOLICITADOS

{{controles_texto}}

▶ IV. APROBACIÓN

Jefe Inmediato:          {{jefe_inmediato}}
Responsable del Área:    {{responsable_area}}
"""


FORM_FIELDS = [
    # ── I. DATOS GENERALES (14 campos, en el orden exacto de T-APPS) ──
    {
        'name': 'tipo_solicitud',
        'label': '📋 Tipo de Solicitud',
        'type': 'select',
        'required': True,
        'options': ['INGRESO', 'MODIFICACIÓN', 'TRASLADO'],
        'hint': "El tipo de solicitud 'TRASLADO' aplica cuando el empleado cambia de unidad de negocio/empresa."
    },
    {
        'name': 'unidad_negocio',
        'label': '🏭 Unidad de Negocio',
        'type': 'select',
        'required': True,
        'options': ['MANUFACTURAS ELIOT', 'PASH', 'PRIMATELA']
    },
    {
        'name': 'documento',
        'label': '🪪 Documento',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: 3852273 (sin puntos ni guiones)'
    },
    {
        'name': 'nombre',
        'label': '👤 Nombre completo',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: ROSARIO MARISCAL PÉREZ'
    },
    {
        'name': 'cargo',
        'label': '💼 Cargo',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: LÍDER DE TIENDA'
    },
    {
        'name': 'numero_contacto',
        'label': '📞 Número de Contacto',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: +591 77631301'
    },
    {
        'name': 'ubicacion',
        'label': '📍 Ubicación',
        'type': 'select',
        'required': True,
        'options': [
            'Eliot Calle 19',
            'Eliot Manrique',
            'Pash Centro',
            'Pash Retail',
            'Primatela Bogotá',
            'Colombia',
            'Bolivia',
            'Panamá',
            'Otros países',
        ]
    },
    {
        'name': 'fecha_ingreso',
        'label': '📅 Fecha de Ingreso',
        'type': 'date',
        'required': True,
        'placeholder': 'dd/mm/aaaa'
    },
    {
        'name': 'division_centro_costo',
        'label': '💰 División / Centro de Costo',
        'type': 'text',
        'required': True,
        'placeholder': 'Ej: 21700001151800000002 - VENTAS PORTOFINO'
    },
    {
        'name': 'jefe_inmediato',
        'label': '👔 Jefe Inmediato (aprobador 1)',
        'type': 'user_select',
        'required': True,
        'role_filter': 'admin,technician,employee',
        'placeholder': 'Buscar y seleccionar…'
    },
    {
        'name': 'gerencia_area',
        'label': '🏢 Gerencia / Área',
        'type': 'select',
        'required': True,
        'options': [
            'COMERCIAL',
            'FINANCIERA',
            'OPERACIONES',
            'PRODUCCIÓN',
            'LOGÍSTICA',
            'RECURSOS HUMANOS',
            'TECNOLOGÍA (TI)',
            'MERCADEO',
            'DISEÑO',
            'DIRECCIÓN GENERAL',
        ]
    },
    {
        'name': 'tipo_contrato',
        'label': '📄 Tipo de Contrato',
        'type': 'select',
        'required': True,
        'options': ['FIJO', 'TEMPORAL', 'CONTRATISTA', 'PRÁCTICAS', 'OTRO']
    },
    {
        'name': 'reemplazo',
        'label': '🔁 ¿Es reemplazo?',
        'type': 'select',
        'required': True,
        'options': ['NO', 'SÍ']
    },
    {
        'name': 'justificacion',
        'label': '📝 Justificación de los Accesos',
        'type': 'textarea',
        'required': True,
        'placeholder': 'Ejemplo: Se requiere el ingreso de Rosario Mariscal para gestionar la tienda en Santa Cruz. Necesita accesos a Ultrasystem, VPN, correo corporativo y SAP FMS Países ambiente productivo.'
    },

    # ── II. LISTA DE CONTROLES (nuevo tipo control_list) ──
    {
        'name': 'controles',
        'label': '☑ Listado de Controles a solicitar',
        'type': 'control_list',
        'required': True,
        'controls': CONTROLES,
    },

    # ── III. APROBACIÓN (2do aprobador) ──
    # Este user_select captura al Responsable del Área, que el motor de
    # workflow resuelve por user_from_form_field: 'responsable_area'.
    {
        'name': 'responsable_area',
        'label': '✅ Responsable del Área (aprobador 2)',
        'type': 'user_select',
        'required': True,
        'role_filter': 'admin,technician,employee',
        'placeholder': 'Buscar y seleccionar…'
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
        print()
        print(f'[seed] ✅ Terminado. Creadas: {created}, actualizadas: {updated}')
        print(f'[seed] Campos generales: {len(FORM_FIELDS) - 1} + 1 control_list')
        print(f'[seed] Controles disponibles: {len(CONTROLES)}')
        print()
        print('Recordá:')
        print('  • Después de correr este seed, correr:')
        print('    python scripts/seed_workflow_solicitud_usuario.py')
        print('    para que se instale el workflow de aprobación en 2 niveles.')
        print('  • Los aprobadores dinámicos leen los campos:')
        print('    - jefe_inmediato (nivel 1)')
        print('    - responsable_area (nivel 2)')


if __name__ == '__main__':
    run()
