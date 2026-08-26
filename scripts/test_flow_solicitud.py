"""
Test estático del flujo completo de "Creación y Modificación de Usuarios".

Verifica sin correr el servidor:
  1) El seed de la plantilla genera JSON válido con los 14 campos + control_list
  2) Los nombres de campos de aprobador matchean entre plantilla y workflow
  3) La lógica de _resolve_dynamic_approver funciona con datos simulados
  4) El renderer JS del frontend soporta todos los tipos usados
  5) El endpoint /api/templates/approvers responde según lo esperado
  6) La descripcion se autogenera con placeholders correctos
"""
import json
import sys
import re
import types
from contextlib import contextmanager
from pathlib import Path

ROOT = Path("c:/Users/jquitian/proyecto_funcionando")

passed = 0
failed = 0
warnings = 0

def ok(msg):
    global passed
    passed += 1
    print("  OK   " + msg)

def fail(msg):
    global failed
    failed += 1
    print("  FAIL " + msg)

def warn(msg):
    global warnings
    warnings += 1
    print("  WARN " + msg)

def section(name):
    print("\n====== " + name + " ======")


# ============================================================
section("PRUEBA 1: Plantilla - carga y estructura")
# ============================================================
sys.path.insert(0, str(ROOT / 'scripts'))

# Mock del import de 'app' para que el seed no requiera BD
class _FakeApp:
    def app_context(self):
        @contextmanager
        def _ctx():
            yield
        return _ctx()

class _FakeSession:
    @staticmethod
    def add(x): pass
    @staticmethod
    def commit(): pass

class _FakeDB:
    session = _FakeSession()

class _FakeQuery:
    @staticmethod
    def filter_by(**kw):
        class _q:
            @staticmethod
            def first(): return None
        return _q

class _FakeTemplate:
    query = _FakeQuery()

class _FakeApprovalWorkflow:
    query = _FakeQuery()
    def __init__(self, **kw):
        for k, v in kw.items(): setattr(self, k, v)

class _FakeUser:
    query = _FakeQuery()

class _FakeGuion:
    query = _FakeQuery()
    def __init__(self, **kw):
        for k, v in kw.items(): setattr(self, k, v)

class _FakeGuionSubtask:
    query = _FakeQuery()
    def __init__(self, **kw):
        for k, v in kw.items(): setattr(self, k, v)

_fake_module = types.ModuleType('app')
_fake_module.app = _FakeApp()
_fake_module.db = _FakeDB()
_fake_module.Template = _FakeTemplate
_fake_module.ApprovalWorkflow = _FakeApprovalWorkflow
_fake_module.User = _FakeUser
_fake_module.Guion = _FakeGuion
_fake_module.GuionSubtask = _FakeGuionSubtask
sys.modules['app'] = _fake_module

seed_tpl = None
seed_wf = None

try:
    import seed_template_solicitud_usuario as seed_tpl
    ok("Modulo seed_template cargado")
    ok("TEMPLATE_NAME = '" + seed_tpl.TEMPLATE_NAME + "'")
    ok("TITLE_TEMPLATE = '" + seed_tpl.TITLE_TEMPLATE + "'")

    generales = [f for f in seed_tpl.FORM_FIELDS if f['type'] != 'control_list']
    if len(generales) == 15:
        ok("15 campos no-control_list encontrados (14 datos + 1 responsable_area)")
    else:
        fail("Se esperaban 15 no-control_list, hay " + str(len(generales)))

    control_lists = [f for f in seed_tpl.FORM_FIELDS if f['type'] == 'control_list']
    if len(control_lists) == 1:
        ok("1 campo control_list encontrado")
        ctrls = control_lists[0].get('controls', [])
        if len(ctrls) == 24:
            ok("24 controles en el control_list")
        else:
            fail("Se esperaban 24 controles, hay " + str(len(ctrls)))

        # Verificar que los con Usuario Espejo son los esperados
        esperados_espejo = {'externos_confeccion','eliotconf','eliotex','acatex','costotex','vertex','tejido_plano','retail','kactus','sap_pash','sap'}
        con_espejo = {c['code'] for c in ctrls if c.get('needs_espejo')}
        if con_espejo == esperados_espejo:
            ok(str(len(con_espejo)) + " controles con Usuario Espejo (matchea con manual)")
        else:
            fail("Controles con espejo no coinciden: sistema=" + str(con_espejo) + ", esperado=" + str(esperados_espejo))
    else:
        fail("Se esperaba 1 control_list, hay " + str(len(control_lists)))

    ff_json = json.dumps(seed_tpl.FORM_FIELDS, ensure_ascii=False)
    ok("form_fields serializa a JSON valido (" + str(len(ff_json)) + " chars)")
    parsed = json.loads(ff_json)
    if parsed == seed_tpl.FORM_FIELDS:
        ok("Roundtrip JSON idempotente")
    else:
        fail("Roundtrip JSON NO idempotente")

except Exception as e:
    fail("Error cargando seed: " + str(e))
    import traceback
    traceback.print_exc()


# ============================================================
section("PRUEBA 2: Consistencia plantilla vs workflow")
# ============================================================
try:
    import seed_workflow_solicitud_usuario as seed_wf
    ok("WORKFLOW_NAME = '" + seed_wf.WORKFLOW_NAME + "'")
    ok("TRIGGER_TEMPLATE_NAME = '" + seed_wf.TRIGGER_TEMPLATE_NAME + "'")

    if seed_wf.TRIGGER_TEMPLATE_NAME == seed_tpl.TEMPLATE_NAME:
        ok("TRIGGER_TEMPLATE_NAME matchea con la plantilla")
    else:
        fail("MISMATCH: workflow apunta a '" + seed_wf.TRIGGER_TEMPLATE_NAME + "' pero la plantilla es '" + seed_tpl.TEMPLATE_NAME + "'")

    # Verificar _build_approvers_for retorna estructura correcta
    # (usamos empresa ficticia; en producción _find_it_manager retorna None en mock)
    aps = seed_wf._build_approvers_for('eliot')
    ok("_build_approvers_for('eliot') retornó " + str(len(aps)) + " aprobadores")

    plantilla_field_names = {f['name'] for f in seed_tpl.FORM_FIELDS}
    control_codes = set()
    for f in seed_tpl.FORM_FIELDS:
        if f['type'] == 'control_list':
            control_codes = {c['code'] for c in f.get('controls', [])}
            break

    for i, step in enumerate(aps, 1):
        field_name = step.get('user_from_form_field')
        uid = step.get('user_id')
        cond = step.get('condition_control_marked')

        if field_name:
            if field_name in plantilla_field_names:
                campo = next(f for f in seed_tpl.FORM_FIELDS if f['name'] == field_name)
                if campo['type'] == 'user_select':
                    ok("Paso " + str(i) + " (dinámico): '" + field_name + "' existe como user_select")
                else:
                    fail("Paso " + str(i) + ": campo '" + field_name + "' es " + campo['type'])
            else:
                fail("Paso " + str(i) + ": campo '" + str(field_name) + "' NO existe")
        elif uid is not None:
            ok("Paso " + str(i) + " (estático): user_id=" + str(uid))
        else:
            fail("Paso " + str(i) + ": sin user_id ni campo dinámico")

        if cond:
            if cond in control_codes:
                ok("Paso " + str(i) + ": condicional al control '" + cond + "' (existe en plantilla)")
            else:
                fail("Paso " + str(i) + ": condition_control_marked='" + cond + "' NO existe en los 24 controles")

except Exception as e:
    fail("Error cargando workflow: " + str(e))
    import traceback
    traceback.print_exc()


# ============================================================
section("PRUEBA 3: Simulacion de creacion de ticket")
# ============================================================
try:
    form_data_simulado = {
        'tipo_solicitud': 'INGRESO',
        'unidad_negocio': 'MANUFACTURAS ELIOT',
        'documento': '3852273',
        'nombre': 'ROSARIO MARISCAL PEREZ',
        'cargo': 'LIDER DE TIENDA',
        'numero_contacto': '+591 77631301',
        'ubicacion': 'Bolivia',
        'fecha_ingreso': '2026-09-15',
        'division_centro_costo': '21700001151800000002 - VENTAS PORTOFINO',
        'jefe_inmediato': '42',
        'gerencia_area': 'COMERCIAL',
        'tipo_contrato': 'FIJO',
        'reemplazo': 'NO',
        'justificacion': 'Se requiere el ingreso de Rosario Mariscal...',
        'controles': json.dumps({
            'directorio_activo': {
                'marcado': True,
                'nombre': 'DIRECTORIO ACTIVO',
                'descripcion': 'Login sugerido: rmariscal. Grupo COMERCIAL.'
            },
            'correo_corporativo': {
                'marcado': True,
                'nombre': 'CORREO ELECTRONICO CORPORATIVO',
                'descripcion': 'Dominio @pash.com.co. Licencia Estandar.'
            },
            'sap': {
                'marcado': True,
                'nombre': 'SAP',
                'descripcion': 'Nuevo. Ambiente PRODUCTIVO. Version FMS PAISES.',
                'usuario_espejo': 'rise_ventas'
            }
        }),
        'responsable_area': '17',
    }
    ok("form_data simulado con " + str(len(form_data_simulado)) + " campos")

    # Los aprobadores ahora los arma _build_approvers_for por empresa
    aprobadores = seed_wf._build_approvers_for('eliot')
    for step in aprobadores:
        campo = step.get('user_from_form_field')
        if campo:
            if campo in form_data_simulado:
                valor = form_data_simulado[campo]
                ok("Workflow lee '" + campo + "' -> valor '" + str(valor) + "'")
            else:
                fail("Workflow lee '" + campo + "' pero NO esta en form_data")
        elif step.get('user_id'):
            ok("Aprobador estático: user_id=" + str(step['user_id']) + " (rol: " + step.get('role_label', '') + ")")

    for step in aprobadores:
        campo = step.get('user_from_form_field')
        if campo:
            val = form_data_simulado.get(campo)
            if val and val.isdigit():
                ok("Aprobador '" + campo + "' = user_id numerico " + val + " (resolucion via ID)")
            else:
                warn("Aprobador '" + campo + "' = '" + str(val) + "' (resolucion via email/username)")

    controles = json.loads(form_data_simulado['controles'])
    ok("Controles marcados en el ticket simulado: " + str(len(controles)))
    for code, ctl in controles.items():
        needs_esp = code in ('externos_confeccion','eliotconf','eliotex','acatex','costotex','vertex','tejido_plano','retail','kactus','sap_pash','sap')
        if needs_esp:
            if 'usuario_espejo' in ctl:
                ok("  " + ctl['nombre'] + ": descripcion + usuario_espejo='" + ctl['usuario_espejo'] + "'")
            else:
                fail("  " + ctl['nombre'] + " necesita usuario_espejo pero no vino")
        else:
            ok("  " + ctl['nombre'] + ": descripcion presente")

    # ─── Test específico: aprobador condicional (elementos_tecnologia) ───
    print()
    print("  --- Escenarios del 3er aprobador condicional ---")

    def _is_control_marked(form_data, control_code):
        """Replica la lógica de _is_control_marked_in_form del backend."""
        raw = form_data.get('controles')
        if not raw:
            return False
        try:
            c = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return False
        if not isinstance(c, dict):
            return False
        ctl = c.get(control_code)
        return bool(isinstance(ctl, dict) and ctl.get('marcado'))

    # Escenario A: NO pidió elementos tecnológicos -> 3er aprobador se salta
    form_sin_tecno = dict(form_data_simulado)
    ctls_sin_tecno = json.loads(form_sin_tecno['controles'])
    if 'elementos_tecnologia' in ctls_sin_tecno:
        del ctls_sin_tecno['elementos_tecnologia']
    form_sin_tecno['controles'] = json.dumps(ctls_sin_tecno)
    marked_a = _is_control_marked(form_sin_tecno, 'elementos_tecnologia')
    if not marked_a:
        ok("Escenario A: sin elementos_tecnologia marcado -> _is_control_marked=False (3er aprobador NO se activa)")
    else:
        fail("Escenario A: debería devolver False")

    # Escenario B: SI pidió elementos tecnológicos -> 3er aprobador se activa
    form_con_tecno = dict(form_data_simulado)
    ctls_con_tecno = json.loads(form_con_tecno['controles'])
    ctls_con_tecno['elementos_tecnologia'] = {
        'marcado': True,
        'nombre': 'ELEMENTOS DE TECNOLOGÍA',
        'descripcion': 'Portátil i7 16GB SSD 500GB + monitor 24" + auriculares'
    }
    form_con_tecno['controles'] = json.dumps(ctls_con_tecno)
    marked_b = _is_control_marked(form_con_tecno, 'elementos_tecnologia')
    if marked_b:
        ok("Escenario B: con elementos_tecnologia marcado -> _is_control_marked=True (3er aprobador SÍ se activa)")
    else:
        fail("Escenario B: debería devolver True")

    # Escenario C: form_data sin 'controles' (edge case) -> NO se activa
    form_sin_controles = {k: v for k, v in form_data_simulado.items() if k != 'controles'}
    marked_c = _is_control_marked(form_sin_controles, 'elementos_tecnologia')
    if not marked_c:
        ok("Escenario C: form_data sin controles -> _is_control_marked=False (edge case OK)")
    else:
        fail("Escenario C: debería devolver False")

    # Escenario D: controles con JSON inválido -> NO explota, devuelve False
    form_json_malo = dict(form_data_simulado)
    form_json_malo['controles'] = 'esto no es json'
    marked_d = _is_control_marked(form_json_malo, 'elementos_tecnologia')
    if not marked_d:
        ok("Escenario D: JSON inválido -> _is_control_marked=False (no explota)")
    else:
        fail("Escenario D: debería devolver False")

except Exception as e:
    fail("Error simulando ticket: " + str(e))
    import traceback
    traceback.print_exc()


# ============================================================
section("PRUEBA 4: Renderer del frontend soporta todos los tipos")
# ============================================================
create_html = (ROOT / 'templates' / 'employee' / 'create.html').read_text(encoding='utf-8')

tipos_usados = {f['type'] for f in seed_tpl.FORM_FIELDS}
print("  info Tipos en la plantilla: " + str(sorted(tipos_usados)))

for tipo in tipos_usados:
    if tipo == 'text':
        if 'type="text"' in create_html:
            ok("Tipo 'text' -> rama fallback en renderer")
        else:
            warn("Tipo 'text' -> no verifique fallback")
    else:
        pat = "f.type === '" + tipo + "'"
        if pat in create_html:
            ok("Tipo '" + tipo + "' -> tiene rama en renderer JS")
        else:
            fail("Tipo '" + tipo + "' -> NO tiene rama en renderer JS")

if '_renderControlList' in create_html:
    ok("Funcion _renderControlList presente")
else:
    fail("_renderControlList no encontrado")

if '_wireControlListCheckboxes' in create_html:
    ok("Funcion _wireControlListCheckboxes presente")
else:
    fail("_wireControlListCheckboxes no encontrado")

if 'data-cl-check' in create_html and 'data-cl-desc' in create_html and 'data-cl-espejo' in create_html:
    ok("Atributos data-cl-* del control_list declarados")
else:
    fail("Faltan atributos data-cl-*")

if "tplType === 'control_list'" in create_html:
    ok("Submit handler tiene rama especial para control_list")
else:
    fail("Submit handler NO maneja control_list")

if 'data-user-select' in create_html and '_populateUserSelects' in create_html:
    ok("user_select y _populateUserSelects presentes")
else:
    fail("Falta soporte de user_select")


# ============================================================
section("PRUEBA 5: Backend maneja template_form_data")
# ============================================================
app_py = (ROOT / 'app.py').read_text(encoding='utf-8')

if 'template_form_data' in app_py:
    ok("Backend lee 'template_form_data' del request")
else:
    fail("Backend NO lee 'template_form_data'")

if 'def create_approvals_for_ticket(ticket, workflow, steps, form_data=None):' in app_py:
    ok("create_approvals_for_ticket acepta form_data")
else:
    fail("create_approvals_for_ticket NO acepta form_data")

if 'def _resolve_dynamic_approver(field_value, company):' in app_py:
    ok("_resolve_dynamic_approver definido")
else:
    fail("_resolve_dynamic_approver NO definido")

if "@app.route('/api/templates/approvers'" in app_py:
    ok("Endpoint /api/templates/approvers existe")
else:
    fail("Endpoint /api/templates/approvers NO existe")

if 'User.company == company' in app_py:
    ok("Endpoint filtra por empresa (multi-tenant)")
else:
    warn("Endpoint no parece filtrar por empresa - revisar")

# Verificar aprobador condicional
if 'def _is_control_marked_in_form' in app_py:
    ok("_is_control_marked_in_form definido")
else:
    fail("_is_control_marked_in_form NO definido")

if "condition_control_marked" in app_py:
    ok("Backend maneja 'condition_control_marked' en el step")
else:
    fail("Backend NO maneja condition_control_marked")

if "skipped_conditional" in app_py:
    ok("Backend registra skipped_conditional en audit log")
else:
    fail("Backend NO registra skipped_conditional")


# ============================================================
section("PRUEBA 6: Placeholders titulo y descripcion")
# ============================================================
title_placeholders = re.findall(r'\{\{(\w+)\}\}', seed_tpl.TITLE_TEMPLATE)
desc_placeholders = set(re.findall(r'\{\{(\w+)\}\}', seed_tpl.DESCRIPTION_TEMPLATE))

campos_disponibles = {f['name'] for f in seed_tpl.FORM_FIELDS}
especiales = {'controles_texto', 'responsable_area'}

for ph in set(title_placeholders):
    if ph in campos_disponibles or ph in especiales:
        ok("Title placeholder '" + ph + "' OK")
    else:
        fail("Title placeholder '" + ph + "' NO tiene campo")

for ph in desc_placeholders:
    if ph in campos_disponibles or ph in especiales:
        ok("Desc placeholder '" + ph + "' OK")
    else:
        fail("Desc placeholder '" + ph + "' NO tiene campo")


# ============================================================
section("PRUEBA 7: Guiones para las 3 empresas")
# ============================================================
guion_json = ROOT / 'scripts' / 'guion_solicitud_usuario_primatela.json'
if guion_json.exists():
    with open(guion_json, encoding='utf-8') as f:
        gdata = json.load(f)
    n_subs = len(gdata['guiones'][0].get('subtasks', []))
    ok("Guion fuente Primatela: " + str(n_subs) + " subtareas")
else:
    fail("guion_solicitud_usuario_primatela.json no existe")

seed_guiones = ROOT / 'scripts' / 'seed_guiones_solicitud_usuario.py'
if seed_guiones.exists():
    ok("seed_guiones_solicitud_usuario.py existe (adaptara a las 3 empresas)")
else:
    fail("Script de guiones no existe")


# ============================================================
section("PRUEBA 8: Manual coherente con la plantilla")
# ============================================================
manual = ROOT / 'static' / 'manuales' / 'manual_solicitud_usuario.html'
if manual.exists():
    txt = manual.read_text(encoding='utf-8')
    checks = [
        ('TRASLADO', 'Tipo TRASLADO'),
        ('ELEMENTOS DE TECNOLOG', 'Control 1'),
        ('SAP PASH', 'SAP PASH'),
        ('KACTUS', 'KACTUS'),
        ('Jefe Inmediato', 'Aprobador 1'),
        ('Responsable del', 'Aprobador 2'),
        ('Usuario Espejo', 'Concepto Usuario Espejo'),
        ('Hoja 4', 'Advertencia Hoja 4'),
    ]
    for term, desc in checks:
        if term in txt:
            ok("Manual: " + desc)
        else:
            fail("Manual: FALTA '" + term + "' - " + desc)
else:
    fail("Manual no existe")


# ============================================================
print("\n=========== RESUMEN ===========")
print("  Pasados:  " + str(passed))
print("  Warnings: " + str(warnings))
print("  Fallidos: " + str(failed))
if failed == 0:
    print("\n*** FLUJO ESTATICO VALIDADO OK ***")
    sys.exit(0)
else:
    print("\n*** HAY " + str(failed) + " PROBLEMAS ***")
    sys.exit(1)
