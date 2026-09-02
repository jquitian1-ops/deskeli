"""
seed_controles_catalogo.py

Carga el catálogo maestro de Controles (tabla controles_catalogo) con los 24
controles que replican el módulo T-APPS. Idempotente: si un control con el
mismo (code, company) ya existe, lo actualiza; si no, lo crea.

Los controles se cargan como globales (company=NULL) para que sean visibles a
las 3 empresas. Si querés controles específicos por empresa, editá esta lista
o creá controles adicionales desde /admin/controles.

Uso:
    python scripts/seed_controles_catalogo.py
"""
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import app, db, Control


# Catálogo oficial de 28 controles según el documento
# "LISTA CONSOLIDADA DE CONTROLES" (controles.pdf). Las descripciones
# reproducen el "Detalle del control" del PDF para que el solicitante vea
# la misma guía operativa que usan hoy en T-APPS.
CATALOGO = [
    # 1
    {'code': 'elementos_tecnologia', 'name': 'ELEMENTOS DE TECNOLOGIA',
     'descripcion': 'Seleccione los elementos de tecnología que requiera solicitar. Esto está sujeto a posterior aprobación de las gerencias de área por costos.',
     'tipo': 'elemento', 'needs_espejo': False, 'costo_referencia': None},
    # 2
    {'code': 'herramientas_ofimaticas', 'name': 'HERRAMIENTAS OFIMATICAS',
     'descripcion': 'Herramientas ofimáticas (seleccione los aplicativos a los cuales requiere acceso y justificación).',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # 3
    {'code': 'directorio_activo', 'name': 'DIRECTORIO ACTIVO',
     'descripcion': 'Usuario para ingresar al equipo de cómputo.',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # 4
    {'code': 'correo_corporativo', 'name': 'CORREO ELECTRONICO CORPORATIVO',
     'descripcion': 'Dirección de correo electrónico corporativo (indicar el dominio, ejemplo: @tekstelas.com; @patprimo.com.co; @pash.com.co; @patprimo.co; etc.). Adicional indicar justificación y tipo de licencia (solo correo, básica o estándar).',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # 5
    {'code': 'creacion_vpn', 'name': 'CREACION VPN',
     'descripcion': 'Se requiere para conexión a los aplicativos en modalidad teletrabajo.',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # 6
    {'code': 'carpetas_compartidas', 'name': 'CARPETAS COMPARTIDAS',
     'descripcion': 'Carpetas compartidas (por favor indicar la ruta de la carpeta donde requiere el acceso).',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # 7
    {'code': 'permiso_imprimir', 'name': 'PERMISO DE IMPRIMIR',
     'descripcion': 'Permisos de impresión (BYN; para opción de color está sujeto a aprobación por Dirección de Operaciones e Infraestructura).',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # 8
    {'code': 'permisos_internet', 'name': 'PERMISOS DE INTERNET',
     'descripcion': 'Debe detallar las páginas a las cuales van a acceder y especificar la categoría que requiere: - AVANZADO (VIP): aplica si requiere redes sociales, permite un acceso más amplio con restricciones mínimas. - BÁSICO (STAFF): ofrece un nivel básico de acceso con filtros más restrictivos.',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # 9
    {'code': 'puntos_electricos_red', 'name': 'PUNTOS ELECTRICOS O RED',
     'descripcion': 'Describa si es revisión o nuevos; adicional las cantidades de puntos de red y/o eléctricos que se requiere si son puntos nuevos.',
     'tipo': 'elemento', 'needs_espejo': False, 'costo_referencia': None},
    # 10
    {'code': 'sql_gerber', 'name': 'SQL GERBER',
     'descripcion': 'Permisos SQL Gerber; se debe informar el nombre de la carpeta y el tipo de permiso (lectura, escritura o lectura/escritura).',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # 11
    {'code': 'puertos_usb', 'name': 'PUERTOS USB',
     'descripcion': 'Habilitación de puertos USB (deben justificar por qué se requiere el acceso).',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # 12
    {'code': 'externos_confeccion', 'name': 'EXTERNOS CONFECCION',
     'descripcion': 'Usuario para ingreso al aplicativo Externos Confección (deben indicar en su respectivo campo el Usuario Espejo, este debe estar activo en la compañía).',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # 13
    {'code': 'eliotconf', 'name': 'ELIOTCONF',
     'descripcion': 'Usuario para ingreso al aplicativo Eliotconf (deben indicar en su respectivo campo el Usuario Espejo, este debe estar activo en la compañía).',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # 14
    {'code': 'eliotex', 'name': 'ELIOTEX',
     'descripcion': 'Usuario para ingreso al aplicativo Eliotex (deben indicar en su respectivo campo el Usuario Espejo, este debe estar activo en la compañía).',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # 15
    {'code': 'acatex', 'name': 'ACATEX',
     'descripcion': 'Usuario para ingreso al aplicativo Acatex (deben indicar en su respectivo campo el Usuario Espejo, este debe estar activo en la compañía).',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # 16
    {'code': 'costotex', 'name': 'COSTOTEX',
     'descripcion': 'Usuario para ingreso al aplicativo Costotex (deben indicar en su respectivo campo el Usuario Espejo, este debe estar activo en la compañía).',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # 17
    {'code': 'vertex', 'name': 'VERTEX',
     'descripcion': 'Usuario para ingreso al aplicativo Vertex (deben indicar en su respectivo campo el Usuario Espejo, este debe estar activo en la compañía).',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # 18
    {'code': 'tejido_plano', 'name': 'TEJIDO PLANO',
     'descripcion': 'Usuario para ingreso al aplicativo Tejido Plano (deben indicar en su respectivo campo el Usuario Espejo, este debe estar activo en la compañía).',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # 19 (nuevo respecto al catálogo previo)
    {'code': 'bodega_telas', 'name': 'BODEGA DE TELAS',
     'descripcion': 'Usuario para ingreso al aplicativo Bodega de Telas (deben indicar en su respectivo campo el Usuario Espejo, este debe estar activo en la compañía).',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # 20 (nuevo)
    {'code': 'separacion_telas', 'name': 'SEPARACION DE TELAS',
     'descripcion': 'Usuario para ingreso al aplicativo Separación de Telas (deben indicar en su respectivo campo el Usuario Espejo, este debe estar activo en la compañía).',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # 21 (nuevo)
    {'code': 'ventas_movil', 'name': 'VENTAS MOVIL',
     'descripcion': 'Usuario para ingreso al aplicativo Ventas Móvil.',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # 22 (nuevo)
    {'code': 'ultrasystem', 'name': 'ULTRASYSTEM',
     'descripcion': 'Permisos en plataforma Ultrasystem; se debe indicar Usuario Espejo activo, para qué país y marcas requiere el acceso.',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # 23
    {'code': 'retail', 'name': 'RETAIL',
     'descripcion': 'Usuario para ingreso al aplicativo Retail (deben indicar en su respectivo campo el Usuario Espejo, este debe estar activo en la compañía). Especificar para qué país y marcas requiere los accesos.',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # 24
    {'code': 'skycm', 'name': 'SKYCM',
     'descripcion': 'Solicitud al aplicativo SkyCM Market Place (asesores comerciales).',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # 25
    {'code': 'biotime', 'name': 'BIOTIME',
     'descripcion': 'BioTime; indicar el país y Usuario Espejo donde requiere el acceso.',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # 26
    {'code': 'kactus', 'name': 'KACTUS',
     'descripcion': 'Plataforma de acceso a módulos de nómina y gestión humana a nivel de creación de usuarios, permisos, accesos a programas, roles y tipo de usuario.',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # 27 — SOLO aplica para tipo de solicitud MODIFICACION (filtrado en el frontend)
    {'code': 'sap_pash', 'name': 'SAP PASH',
     'descripcion': 'Solo seleccionar cuando sea tipo de solicitud MODIFICACIÓN y ya cuente con usuario en el aplicativo SAP PASH.',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # 28
    {'code': 'sap', 'name': 'SAP',
     'descripcion': 'En el campo descripción indicar si ya cuenta con usuario; adicional deben indicar el Usuario Espejo y el ambiente (Productivo, Preproductivo, Calidad, Desarrollo). Indicar versión (AFS, FMS PASH, FMS PAISES, EWM, RISE).',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
]


def run():
    with app.app_context():
        created, updated = 0, 0
        for row in CATALOGO:
            existing = Control.query.filter_by(code=row['code'], company=None).first()
            if existing:
                existing.name = row['name']
                existing.descripcion = row['descripcion']
                existing.tipo = row['tipo']
                existing.needs_espejo = row['needs_espejo']
                existing.costo_referencia = row['costo_referencia']
                existing.is_active = True
                updated += 1
            else:
                c = Control(
                    code=row['code'],
                    name=row['name'],
                    descripcion=row['descripcion'],
                    tipo=row['tipo'],
                    needs_espejo=row['needs_espejo'],
                    costo_referencia=row['costo_referencia'],
                    company=None,  # global
                    is_active=True,
                )
                db.session.add(c)
                created += 1
        db.session.commit()
        print(f'[seed] Catalogo de controles: {created} creados, {updated} actualizados. Total: {len(CATALOGO)}')


if __name__ == '__main__':
    run()
