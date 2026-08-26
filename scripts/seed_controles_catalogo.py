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


CATALOGO = [
    # ── Equipos y ofimática ──
    {'code': 'elementos_tecnologia', 'name': 'ELEMENTOS DE TECNOLOGIA',
     'descripcion': 'Portátil, monitor, teclado, mouse, diadema, docking, etc. Especifique modelo y accesorios.',
     'tipo': 'elemento', 'needs_espejo': False, 'costo_referencia': None},
    {'code': 'herramientas_ofimaticas', 'name': 'HERRAMIENTAS OFIMATICAS',
     'descripcion': 'Microsoft 365, Office, licencias específicas.',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # ── Red / correo / VPN / carpetas ──
    {'code': 'directorio_activo', 'name': 'DIRECTORIO ACTIVO',
     'descripcion': 'Creación de usuario de red / dominio.',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    {'code': 'correo_corporativo', 'name': 'CORREO ELECTRONICO CORPORATIVO',
     'descripcion': 'Alias, buzón, grupos de distribución.',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    {'code': 'creacion_vpn', 'name': 'CREACION VPN',
     'descripcion': 'Acceso remoto a la red corporativa.',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    {'code': 'carpetas_compartidas', 'name': 'CARPETAS COMPARTIDAS',
     'descripcion': 'Rutas de red (\\\\servidor\\carpeta) con permisos R/W.',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # ── Permisos ──
    {'code': 'permiso_imprimir', 'name': 'PERMISO DE IMPRIMIR',
     'descripcion': 'Colas de impresión departamentales o específicas.',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    {'code': 'permisos_internet', 'name': 'PERMISOS DE INTERNET',
     'descripcion': 'Perfil de navegación en el proxy (básico, avanzado, sin restricción).',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    {'code': 'puntos_electricos_red', 'name': 'PUNTOS ELECTRICOS O RED',
     'descripcion': 'Habilitar tomas eléctricas o de red en la ubicación asignada.',
     'tipo': 'elemento', 'needs_espejo': False, 'costo_referencia': None},
    {'code': 'sql_gerber', 'name': 'SQL GERBER',
     'descripcion': 'Acceso a BD SQL / Gerber (moldes, patronaje).',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    {'code': 'puertos_usb', 'name': 'PUERTOS USB',
     'descripcion': 'Habilitar puertos USB en el equipo (por defecto bloqueados por política).',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # ── Aplicativos textiles (con Usuario Espejo) ──
    {'code': 'externos_confeccion', 'name': 'EXTERNOS CONFECCION',
     'descripcion': 'Módulo para satélites/talleres externos.',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    {'code': 'eliotconf', 'name': 'ELIOTCONF',
     'descripcion': 'Sistema de confección Eliot.',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    {'code': 'eliotex', 'name': 'ELIOTEX',
     'descripcion': 'Sistema Eliot Textil.',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    {'code': 'acatex', 'name': 'ACATEX',
     'descripcion': 'Sistema de acabados textiles.',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    {'code': 'costotex', 'name': 'COSTOTEX',
     'descripcion': 'Sistema de costos textiles.',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    {'code': 'vertex', 'name': 'VERTEX',
     'descripcion': 'Sistema Vertex (integración).',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    {'code': 'tejido_plano', 'name': 'TEJIDO PLANO',
     'descripcion': 'Módulo tejido plano.',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    # ── Comercial / retail ──
    {'code': 'retail', 'name': 'RETAIL',
     'descripcion': 'Aplicativo POS / retail.',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    {'code': 'skycm', 'name': 'SKYCM',
     'descripcion': 'Aplicativo SKYCM.',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    {'code': 'biotime', 'name': 'BIOTIME',
     'descripcion': 'Control de asistencia biométrico.',
     'tipo': 'acceso', 'needs_espejo': False, 'costo_referencia': None},
    # ── SAP y KACTUS ──
    {'code': 'kactus', 'name': 'KACTUS',
     'descripcion': 'Nómina KACTUS. Especifique módulos y perfil.',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    {'code': 'sap_pash', 'name': 'SAP PASH',
     'descripcion': 'Instancia SAP de Pash. Especifique ambiente (PRD/QAS/DEV), mandante y módulos.',
     'tipo': 'acceso', 'needs_espejo': True, 'costo_referencia': None},
    {'code': 'sap', 'name': 'SAP',
     'descripcion': 'SAP genérico. Especifique ambiente, mandante, módulos, tcodes.',
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
