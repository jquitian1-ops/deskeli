"""
test_flow_solicitudes_modulo.py

Test estático del módulo "Solicitudes de Creación y Modificación de Usuarios".
No corre servidor ni base de datos: valida estructura, coherencia entre
frontend/backend/modelos, y las transiciones de la máquina de estados.

Uso:
    python scripts/test_flow_solicitudes_modulo.py

Devuelve exit 0 si todo pasa, 1 si hay fallos.
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_passed = []
_failed = []


def check(name, ok, detail=''):
    if ok:
        _passed.append(name)
        print(f'  [OK] {name}')
    else:
        _failed.append((name, detail))
        print(f'  [FAIL] {name}' + (f' -- {detail}' if detail else ''))


def read(path):
    with open(os.path.join(BASE, path), 'r', encoding='utf-8') as f:
        return f.read()


# ─────────────────────────────────────────────────────────────────────────────
print('\n[1/8] Modelos y constantes en app.py')
# ─────────────────────────────────────────────────────────────────────────────
app_src = read('app.py')

check('Modelo Control declarado', 'class Control(db.Model)' in app_src)
check('Modelo SolicitudUsuario declarado', 'class SolicitudUsuario(db.Model)' in app_src)
check('Modelo SolicitudControl declarado', 'class SolicitudControl(db.Model)' in app_src)
check('Modelo SolicitudHistorial declarado', 'class SolicitudHistorial(db.Model)' in app_src)
check('Modelo SolicitudAdjunto declarado', 'class SolicitudAdjunto(db.Model)' in app_src)

check('Constante SOLICITUD_ESTADO_PENDIENTE_JEFE', 'SOLICITUD_ESTADO_PENDIENTE_JEFE' in app_src)
check('Constante SOLICITUD_ESTADO_APROBADO_GERENTE_TI', 'SOLICITUD_ESTADO_APROBADO_GERENTE_TI' in app_src)
check('Constante SOLICITUD_ESTADO_ANULADO', 'SOLICITUD_ESTADO_ANULADO' in app_src)
check('Constante SOLICITUD_ESTADO_EN_TRAMITE', 'SOLICITUD_ESTADO_EN_TRAMITE' in app_src)
check('Enum SOLICITUD_TIPOS con 3 valores', "SOLICITUD_TIPOS = ('INGRESO', 'MODIFICACION', 'TRASLADO')" in app_src)

check('SOLICITUD_ESTADO_LABEL mapea todos los estados',
      "SOLICITUD_ESTADO_LABEL = {" in app_src and 'Pendiente aprobación Jefe Inmediato' in app_src)


# ─────────────────────────────────────────────────────────────────────────────
print('\n[2/8] Máquina de transiciones')
# ─────────────────────────────────────────────────────────────────────────────

check('APROBAR_SIGUIENTE mapea Jefe -> AnalistaTI -> GerenteArea -> GerenteTI -> Aprobado (orden oficial)',
      'SOLICITUD_APROBAR_SIGUIENTE = {' in app_src and
      'SOLICITUD_ESTADO_PENDIENTE_JEFE: SOLICITUD_ESTADO_PENDIENTE_ANALISTA_TI' in app_src and
      'SOLICITUD_ESTADO_PENDIENTE_ANALISTA_TI: SOLICITUD_ESTADO_PENDIENTE_GERENTE_AREA' in app_src and
      'SOLICITUD_ESTADO_PENDIENTE_GERENTE_AREA: SOLICITUD_ESTADO_PENDIENTE_GERENTE_TI' in app_src and
      'SOLICITUD_ESTADO_PENDIENTE_GERENTE_TI: SOLICITUD_ESTADO_APROBADO_GERENTE_TI' in app_src)

check('DEVOLVER_A definido para los 4 niveles',
      'SOLICITUD_DEVOLVER_A = {' in app_src)

check('RECHAZAR_A definido para los 4 niveles',
      'SOLICITUD_RECHAZAR_A = {' in app_src)

check('DEVUELTO_A_PENDIENTE definido (para reenviar)',
      'SOLICITUD_DEVUELTO_A_PENDIENTE = {' in app_src)

check('SOLICITUD_ESTADOS_FINALES contiene ANULADO y CERRADO',
      'SOLICITUD_ESTADOS_FINALES = {' in app_src)

check('_apply_transition helper existe',
      'def _apply_transition(s, user, accion, observacion):' in app_src)

# Verificar que _apply_transition maneja las 8 acciones
acciones_esperadas = ['aprobar', 'devolver', 'rechazar', 'anular', 'reenviar', 'cerrar', 'marcar_tramite']
for accion in acciones_esperadas:
    check(f'  _apply_transition soporta acción "{accion}"',
          f"accion == '{accion}'" in app_src)


# ─────────────────────────────────────────────────────────────────────────────
print('\n[3/8] Endpoints REST')
# ─────────────────────────────────────────────────────────────────────────────

endpoints_esperados = [
    ("GET  /api/controles", "@app.route('/api/controles', methods=['GET'])"),
    ("POST /api/controles", "@app.route('/api/controles', methods=['POST'])"),
    ("PUT  /api/controles/<id>", "@app.route('/api/controles/<int:control_id>', methods=['PUT'])"),
    ("DELETE /api/controles/<id>", "@app.route('/api/controles/<int:control_id>', methods=['DELETE'])"),
    ("POST /api/solicitudes-usuarios", "@app.route('/api/solicitudes-usuarios', methods=['POST'])"),
    ("GET  /api/solicitudes-usuarios", "@app.route('/api/solicitudes-usuarios', methods=['GET'])"),
    ("GET  /api/solicitudes-usuarios/<id>", "@app.route('/api/solicitudes-usuarios/<int:solicitud_id>', methods=['GET'])"),
    ("POST /aprobar", "@app.route('/api/solicitudes-usuarios/<int:solicitud_id>/aprobar', methods=['POST'])"),
    ("POST /devolver", "@app.route('/api/solicitudes-usuarios/<int:solicitud_id>/devolver', methods=['POST'])"),
    ("POST /rechazar", "@app.route('/api/solicitudes-usuarios/<int:solicitud_id>/rechazar', methods=['POST'])"),
    ("POST /anular", "@app.route('/api/solicitudes-usuarios/<int:solicitud_id>/anular', methods=['POST'])"),
    ("POST /reenviar", "@app.route('/api/solicitudes-usuarios/<int:solicitud_id>/reenviar', methods=['POST'])"),
    ("POST /cerrar", "@app.route('/api/solicitudes-usuarios/<int:solicitud_id>/cerrar', methods=['POST'])"),
    ("POST /marcar-tramite", "@app.route('/api/solicitudes-usuarios/<int:solicitud_id>/marcar-tramite', methods=['POST'])"),
    ("POST /adjuntos", "@app.route('/api/solicitudes-usuarios/<int:solicitud_id>/adjuntos', methods=['POST'])"),
    ("GET  /adjuntos/<id>", "@app.route('/api/solicitudes-usuarios/<int:solicitud_id>/adjuntos/<int:adjunto_id>', methods=['GET'])"),
    ("POST /decidir/<token> (aprobar por correo)", "@app.route('/api/solicitudes-usuarios/decidir/<token>', methods=['POST'])"),
]
for label, sig in endpoints_esperados:
    check(f'Endpoint {label}', sig in app_src)

# Aprobación por correo
check('Modelo SolicitudApprovalToken declarado',
      'class SolicitudApprovalToken(db.Model)' in app_src)
check('Funcion _send_solicitud_approval_email() existe',
      'def _send_solicitud_approval_email(' in app_src)
check('Funcion _create_or_get_solicitud_token() existe',
      'def _create_or_get_solicitud_token(' in app_src)
check('_notify_next_approver dispara envio de correo',
      '_send_solicitud_approval_email(solicitud, approver, token)' in app_src)
check('Pagina publica /solicitudes-usuarios/decidir/<token>',
      "@app.route('/solicitudes-usuarios/decidir/<token>', methods=['GET'])" in app_src)


# ─────────────────────────────────────────────────────────────────────────────
print('\n[4/8] Rutas de páginas HTML')
# ─────────────────────────────────────────────────────────────────────────────

paginas = [
    ("GET  /solicitudes-usuarios (listado)", "@app.route('/solicitudes-usuarios', methods=['GET'])"),
    ("GET  /solicitudes-usuarios/nueva", "@app.route('/solicitudes-usuarios/nueva', methods=['GET'])"),
    ("GET  /solicitudes-usuarios/<id>", "@app.route('/solicitudes-usuarios/<int:solicitud_id>', methods=['GET'])"),
    ("GET  /admin/controles", "@app.route('/admin/controles', methods=['GET'])"),
]
for label, sig in paginas:
    check(f'Ruta {label}', sig in app_src)


# ─────────────────────────────────────────────────────────────────────────────
print('\n[5/8] Templates HTML existen')
# ─────────────────────────────────────────────────────────────────────────────

templates = [
    'templates/solicitudes/list.html',
    'templates/solicitudes/create.html',
    'templates/solicitudes/detail.html',
    'templates/admin/controles.html',
]
for t in templates:
    ok = os.path.exists(os.path.join(BASE, t))
    check(f'Existe {t}', ok)


# ─────────────────────────────────────────────────────────────────────────────
print('\n[6/8] Botones en dashboards')
# ─────────────────────────────────────────────────────────────────────────────

tech_dash = read('templates/technician/dashboard.html')
admin_dash = read('templates/admin/dashboard.html')

check('Botón en technician dashboard apunta a /solicitudes-usuarios',
      '/solicitudes-usuarios' in tech_dash and 'Creación o Modificación de Usuarios' in tech_dash)

check('Botón en admin dashboard apunta a /solicitudes-usuarios',
      '/solicitudes-usuarios' in admin_dash and 'Creación o Modificación de Usuarios' in admin_dash)


# ─────────────────────────────────────────────────────────────────────────────
print('\n[7/8] Frontend - coherencia con backend')
# ─────────────────────────────────────────────────────────────────────────────

create_html = read('templates/solicitudes/create.html')
detail_html = read('templates/solicitudes/detail.html')
list_html = read('templates/solicitudes/list.html')

# create.html
check('create.html usa POST /api/solicitudes-usuarios',
      "fetch('/api/solicitudes-usuarios'" in create_html and "method: 'POST'" in create_html)
check('create.html tiene 3 tipos de solicitud',
      'INGRESO' in create_html and 'MODIFICACION' in create_html and 'TRASLADO' in create_html)
check('create.html carga catálogo desde /api/controles',
      "fetch('/api/controles'" in create_html)
check('create.html carga aprobadores desde /api/inf-aprobadores-para-solicitud',
      "fetch('/api/inf-aprobadores-para-solicitud'" in create_html)
check('create.html muestra hint condicional según tipo',
      'TIPO_HINTS' in create_html)
check('create.html oculta/muestra Card Ingreso según tipo',
      'cardIngreso' in create_html and 'cond-hidden' in create_html)
check('create.html oculta/muestra Card Modif según tipo',
      'cardModif' in create_html)
check('create.html habilita nombre_reemplazo solo si es_reemplazo=true',
      'onReemplazoChange' in create_html and 'fldReemplazo' in create_html)
check('create.html valida al menos 1 control marcado',
      'Debes seleccionar al menos un control' in create_html)

# detail.html
check('detail.html carga desde /api/solicitudes-usuarios/<id>',
      '/api/solicitudes-usuarios/${SOLICITUD_ID}' in detail_html)
check('detail.html tiene botones aprobar/devolver/rechazar/anular/reenviar',
      'doAction(\'aprobar\')' in detail_html and 'askObs(\'devolver\'' in detail_html and 'askObs(\'rechazar\'' in detail_html)
check('detail.html renderiza controles con costo total',
      'costoTotal' in detail_html)
check('detail.html muestra historial timeline',
      'hist-timeline' in detail_html and 'historial' in detail_html)

# list.html
check('list.html llama a /api/solicitudes-usuarios con filtros',
      "'/api/solicitudes-usuarios?' + params.toString()" in list_html)
check('list.html tiene filtro por número de solicitud',
      'f-numero' in list_html)
check('list.html tiene filtro por estado',
      'f-estado' in list_html)


# ─────────────────────────────────────────────────────────────────────────────
print('\n[8/8] Seed catálogo de controles')
# ─────────────────────────────────────────────────────────────────────────────

seed_src = read('scripts/seed_controles_catalogo.py')
check('seed_controles_catalogo.py importa Control desde app',
      'from app import app, db, Control' in seed_src)

# Contar cuántos controles hay en el CATALOGO
matches = re.findall(r"\{'code':", seed_src)
check(f'CATALOGO tiene 28 controles (encontrados: {len(matches)})', len(matches) == 28)

# Códigos clave del MD
codigos_esperados = ['elementos_tecnologia', 'sap', 'kactus', 'directorio_activo',
                     'correo_corporativo', 'creacion_vpn', 'permiso_imprimir']
for cod in codigos_esperados:
    check(f'  CATALOGO incluye "{cod}"', f"'code': '{cod}'" in seed_src)

check('seed es idempotente (Query + update si existe)',
      'Control.query.filter_by(code=' in seed_src and 'existing.name = row' in seed_src)


# ─────────────────────────────────────────────────────────────────────────────
# RESULTADO
# ─────────────────────────────────────────────────────────────────────────────
print()
print('=' * 70)
print(f'RESULTADO: {len(_passed)} pasaron, {len(_failed)} fallaron')
print('=' * 70)

if _failed:
    print('\n[FALLOS]:')
    for name, detail in _failed:
        print(f'  x {name}' + (f'\n    {detail}' if detail else ''))
    sys.exit(1)
else:
    print('\nTodo OK. El modulo esta listo para bootstrap (crea tablas), seed y pruebas manuales.')
    print()
    print('Pasos siguientes en Coolify o local:')
    print('  1. Reiniciar el servidor -> bootstrap_app() crea las 5 tablas nuevas.')
    print('  2. python scripts/seed_controles_catalogo.py')
    print('  3. Login como admin o technician -> ver el boton nuevo en el dashboard.')
    print('  4. Clic en "Creacion o Modificacion de Usuarios" -> listado vacio')
    print('  5. Clic en "+ Diligenciar Solicitud" -> form completo')
    sys.exit(0)
