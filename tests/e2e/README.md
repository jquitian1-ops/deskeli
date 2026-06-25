# TicketDesk Enterprise - E2E Tests con Playwright

Tests end-to-end (E2E) profesionales para TicketDesk Enterprise usando Playwright.

## Estructura

```
tests/e2e/
├── pages/                               # Page Object Models (POM)
│   ├── __init__.py
│   ├── LoginPage.py                     # Autenticación
│   ├── EmployeeDashboardPage.py         # Portal de empleados
│   ├── TechnicianDashboardPage.py       # Portal de técnicos
│   └── AdminDashboardPage.py            # Portal de administrador
├── conftest.py                          # Fixtures y configuración
├── test_employee_create_ticket.py       # Escenario 1: Crear ticket
├── test_technician_resolve_ticket.py    # Escenario 2: Resolver ticket
├── test_admin_dashboard_metrics.py      # Escenario 3: Métricas admin
├── playwright.ini                       # Configuración pytest/Playwright
├── requirements-e2e.txt                 # Dependencias
└── README.md                            # Este archivo
```

## Requisitos

- Python 3.10+
- TicketDesk Enterprise running en `http://localhost:5050`

## Instalación

### 1. Instalar dependencias

```bash
pip install -r tests/e2e/requirements-e2e.txt
```

### 2. Instalar navegadores Playwright

```bash
playwright install chromium
# O para todos los navegadores:
playwright install
```

### 3. Configurar variables de entorno

Crear `.env` o exportar:

```bash
# URL base de la aplicación (default: http://localhost:5050)
export TEST_BASE_URL=http://localhost:5050

# false = mostrar navegador, true = headless mode
export TEST_HEADLESS=false
```

## Ejecución

### Ejecutar todos los E2E tests

```bash
# Con navegador visible (headed)
pytest tests/e2e/ --headed

# Sin navegador (headless)
pytest tests/e2e/

# Verbose output
pytest tests/e2e/ -v

# Con pausa entre acciones (debug)
pytest tests/e2e/ --headed --slowmo=100
```

### Ejecutar tests específicos

```bash
# Solo smoke tests (rápidos)
pytest tests/e2e/ -m smoke

# Solo tests lentos
pytest tests/e2e/ -m slow

# Archivo específico
pytest tests/e2e/test_employee_create_ticket.py -v

# Test específico
pytest tests/e2e/test_employee_create_ticket.py::TestEmployeeCreateTicket::test_login_employee_success -v
```

### Generar reportes

```bash
# Reporte HTML
pytest tests/e2e/ --html=tests/e2e/reports/report.html --self-contained-html

# Reporte JSON
pytest tests/e2e/ --json-report --json-report-file=tests/e2e/reports/report.json

# Reporte Allure
pytest tests/e2e/ --alluredir=tests/e2e/reports/allure
allure serve tests/e2e/reports/allure
```

### Debugging

```bash
# Pausar en fallos (pdb)
pytest tests/e2e/ -v --pdb

# Ver logs de navegador
pytest tests/e2e/ -v --capture=no

# Modo slow-motion (útil para debugging)
pytest tests/e2e/ --headed --slowmo=500

# Inspector de Playwright
playwright codegen http://localhost:5050  # Genera código de test interactivamente
```

## Page Object Model (POM)

Cada página está encapsulada en una clase con:
- **Selectores**: Atributos con selectores robustos (data-testid, CSS)
- **Métodos**: Acciones y verificaciones

### Ejemplo: LoginPage

```python
from tests.e2e.pages import LoginPage

# En un test
login_page = LoginPage(page)
login_page.navigate_to_login()
login_page.login(username="john.doe", password="password123")
assert login_page.is_logged_in()
```

### Selectores robustos

Cada selector intenta múltiples opciones:

```python
# LoginPage.INPUT_USERNAME
'[data-testid="username"], input[name="username"], input[type="text"]:first-of-type'
```

Esto permite compatibilidad con diferentes implementaciones HTML.

## Fixtures disponibles

### Autenticación

```python
def test_something(logged_in_employee_page):
    """Page ya tiene empleado logueado"""
    page = logged_in_employee_page

def test_something(test_employee):
    """Credenciales de empleado: username, password, email, etc"""
    assert test_employee["username"] == "john.doe"

def test_something(test_users):
    """Diccionario con todos los usuarios: employee, technician, admin"""
    admin = test_users["admin"]
```

### URLs

```python
def test_something(base_url, login_url, employee_portal_url):
    """URLs de la aplicación"""
    assert login_url == f"{base_url}/login"
```

### Helpers

```python
def test_something(screenshot_helper, full_screenshot_helper):
    """Tomar screenshots"""
    screenshot_helper("my-feature")  # Guarda en tests/e2e/screenshots/
    full_screenshot_helper("page-overview")  # Screenshot de página completa
```

## Escenarios E2E

### Escenario 1: Empleado crea ticket

**Archivo**: `test_employee_create_ticket.py`

**Flujo**:
1. Login como empleado
2. Navegar a "Create Ticket"
3. Llenar título, descripción, prioridad
4. Submitir ticket
5. Verificar ticket aparece en dashboard
6. Verificar SLA calculado
7. Logout

**Tests**:
- `test_login_employee_success`: Validar login
- `test_employee_dashboard_loads`: Dashboard carga
- `test_create_ticket_with_title_and_description`: Crear ticket
- `test_created_ticket_appears_in_dashboard`: Ticket visible
- `test_ticket_sla_calculated`: SLA se calcula
- `test_create_multiple_tickets`: Crear 3 tickets
- `test_logout_employee`: Logout exitoso

### Escenario 2: Técnico resuelve ticket

**Archivo**: `test_technician_resolve_ticket.py`

**Flujo**:
1. Login como técnico
2. Ver cola de trabajo (unassigned tickets)
3. Asignar ticket a sí mismo
4. Cambiar status a "In Progress"
5. Añadir comentarios
6. Resolver ticket con notas
7. Verificar ticket en "Resolved"
8. Logout

**Tests**:
- `test_technician_login_success`: Login técnico
- `test_technician_queue_visible`: Ver cola
- `test_assign_ticket_to_self`: Asignar a sí mismo
- `test_start_work_on_ticket`: Cambiar a In Progress
- `test_add_comment_to_ticket`: Añadir comentario
- `test_resolve_ticket`: Resolver ticket
- `test_verify_resolved_count_increased`: Contador aumenta

### Escenario 3: Admin ve métricas y reportes

**Archivo**: `test_admin_dashboard_metrics.py`

**Flujo**:
1. Login como admin
2. Ver dashboard con métricas
3. Verificar métricas visibles (total, open, resolved, SLA compliance)
4. Verificar gráficos
5. Ir a Reportes
6. Exportar reporte (CSV)
7. Ver log de auditoría
8. Logout

**Tests**:
- `test_admin_login_success`: Login admin
- `test_admin_dashboard_loads`: Dashboard carga
- `test_metrics_visible`: Métricas visibles
- `test_get_dashboard_metrics_values`: Extraer valores
- `test_verify_metric_total_tickets`: Total de tickets
- `test_verify_sla_compliance_metric`: SLA compliance
- `test_charts_visible`: Gráficos visibles
- `test_export_report_csv`: Exportar reporte
- `test_audit_log_visible`: Log auditoría visible

## Usuarios de prueba

Definidos en `conftest.py` (TEST_USERS):

```python
{
    "employee": {
        "username": "john.doe",
        "password": "Test@123456",
        "email": "john.doe@manufacturaseliiot.local",
        "company": "Manufacturas Eliot",
        "role": "employee"
    },
    "technician": {
        "username": "tech.smith",
        "password": "Tech@123456",
        "email": "tech.smith@manufacturaseliiot.local",
        "company": "Manufacturas Eliot",
        "role": "technician"
    },
    "admin": {
        "username": "admin.user",
        "password": "Admin@123456",
        "email": "admin.user@manufacturaseliiot.local",
        "company": "Manufacturas Eliot",
        "role": "admin"
    }
}
```

**Nota**: En producción, estos deberían venir de LDAP/AD real o base de datos de testing.

## Best Practices

### 1. Waits

```python
# ✅ Bueno: wait for element
page.wait_for_selector(selector, timeout=5000)

# ✅ Bueno: wait for navigation
page.wait_for_url(lambda url: "/dashboard" in url)

# ✅ Bueno: wait for network idle
page.wait_for_load_state("networkidle")

# ❌ Malo: sleep (frágil)
time.sleep(2)
```

### 2. Selectores

```python
# ✅ Robusto: data-testid
'[data-testid="create-ticket-button"]'

# ✅ Bueno: aria-label
'[aria-label="Create Ticket"]'

# ✅ Aceptable: CSS
'button.btn-primary'

# ❌ Frágil: XPath completo, index, posición
```

### 3. Assertions

```python
# ✅ Claro
assert login_page.is_logged_in(), "Usuario no está logueado"

# ✅ Descriptivo
assert found_ticket is not None, \
    f"Ticket '{expected_title}' no encontrado en dashboard"

# ❌ Vago
assert result  # ¿Qué resultado?
```

### 4. Logging

```python
# ✅ Useful
print(f"✓ Ticket {ticket_id} creado exitosamente")
print(f"SLA remaining: {sla_value}")

# ✅ En fixture
page.on("console", lambda msg: print(f"[BROWSER] {msg.text}"))
```

## Troubleshooting

### Test timeout

```bash
# Aumentar timeout global
pytest tests/e2e/ --timeout=300

# O en fixture
page.set_default_timeout(60000)  # 60 segundos
```

### Login no funciona

1. Verificar que servidor TicketDesk está running (`http://localhost:5050`)
2. Verificar credenciales en `TEST_USERS` en `conftest.py`
3. Revisar logs del navegador: `pytest -v --capture=no`

### Selectores no encontrados

1. Abrir página en navegador real
2. Usar `playwright codegen` para generar selectores
3. Verificar que elemento es realmente visible en viewport

```bash
playwright codegen http://localhost:5050
```

### Screenshots en failures

Automáticamente guardados en `tests/e2e/screenshots/` cuando test falla.

```python
# O manual en test
screenshot_helper("debug-point-1")
full_screenshot_helper("before-submit")
```

## Integración con CI/CD

### GitHub Actions

```yaml
name: E2E Tests
on: [pull_request, push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r tests/e2e/requirements-e2e.txt
      - run: playwright install chromium
      - run: pytest tests/e2e/ --html=report.html
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: tests/e2e/reports/
```

## Performance Monitoring

Los tests incluyen timeouts:
- Página load: 30 segundos
- Individual action: 30 segundos
- Test completo: 120 segundos (configurable)

Monitorear en reportes HTML para identificar tests lentos.

## Extensiones

### Agregar nuevo Page Object

1. Crear clase en `tests/e2e/pages/NewPage.py`
2. Definir selectores como constantes
3. Implementar métodos para acciones y verificaciones
4. Importar en `tests/e2e/pages/__init__.py`

### Agregar nuevo test

1. Crear archivo `test_*.py` en `tests/e2e/`
2. Usar fixtures de `conftest.py`
3. Usar Page Objects
4. Agregar markers: `@pytest.mark.e2e`, `@pytest.mark.smoke`

## Soporte

Para preguntas o issues:
1. Revisar logs en `tests/e2e/reports/test_run.log`
2. Revisar screenshots en `tests/e2e/screenshots/`
3. Ejecutar test individual con `-vv --capture=no`

---

**Última actualización**: 2026-05-29
**Versión**: 1.0
