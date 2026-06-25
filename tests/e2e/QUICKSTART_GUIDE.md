# E2E Tests - Quick Start Guide

Guía rápida para ejecutar E2E tests de TicketDesk Enterprise con Playwright.

## 30 segundos de Setup

### Windows (PowerShell)

```powershell
# 1. Navegar al proyecto
cd c:\Users\jquitian\proyecto_funcionando

# 2. Ejecutar script de quick start
.\tests\e2e\quickstart.ps1

# O directamente:
pip install -r tests\e2e\requirements-e2e.txt
playwright install chromium
pytest tests\e2e\ --headed
```

### Linux/Mac (Bash)

```bash
# 1. Instalar dependencias
pip install -r tests/e2e/requirements-e2e.txt

# 2. Instalar navegador Playwright
playwright install chromium

# 3. Ejecutar tests
pytest tests/e2e/ --headed

# O con script
bash tests/e2e/quickstart.sh
```

## Comandos Comunes

### Ejecutar todos los tests

```bash
# Con navegador visible
pytest tests/e2e/ --headed

# Sin navegador (headless)
pytest tests/e2e/

# Con reporte HTML
pytest tests/e2e/ --html=tests/e2e/reports/report.html --self-contained-html
```

### Ejecutar tests específicos

```bash
# Solo smoke tests (rápidos)
pytest tests/e2e/ -m smoke --headed

# Escenario 1: Empleado crea ticket
pytest tests/e2e/test_employee_create_ticket.py -v --headed

# Escenario 2: Técnico resuelve ticket
pytest tests/e2e/test_technician_resolve_ticket.py -v --headed

# Escenario 3: Admin ve métricas
pytest tests/e2e/test_admin_dashboard_metrics.py -v --headed

# Test individual
pytest tests/e2e/test_employee_create_ticket.py::TestEmployeeCreateTicket::test_login_employee_success -v --headed
```

### Debugging

```bash
# Ver output completo del navegador
pytest tests/e2e/ --headed --capture=no

# Con pausa entre acciones (útil para debugging)
pytest tests/e2e/ --headed --slowmo=500

# Pausar en fallos
pytest tests/e2e/ --pdb --headed
```

## Requisitos Previos

- ✅ **Python 3.10+** - Instalar desde python.org
- ✅ **TicketDesk running** - `python app.py` en otra terminal
- ✅ **Port 5050** - Servidor accessible en `http://localhost:5050`

## Estructura

```
tests/e2e/
├── pages/                          # Page Object Models
│   ├── LoginPage.py               # Login/logout
│   ├── EmployeeDashboardPage.py   # Crear tickets
│   ├── TechnicianDashboardPage.py # Resolver tickets
│   └── AdminDashboardPage.py      # Métricas y reportes
├── test_employee_create_ticket.py     # Escenario 1 (7 tests)
├── test_technician_resolve_ticket.py  # Escenario 2 (9 tests)
├── test_admin_dashboard_metrics.py    # Escenario 3 (14 tests)
├── conftest.py                    # Fixtures y usuarios de prueba
└── quickstart.ps1 / quickstart.sh # Scripts de inicio rápido
```

## Usuarios de Prueba

Definidos en `conftest.py`:

| Rol | Usuario | Contraseña | Portal |
|-----|---------|-----------|--------|
| Empleado | john.doe | Test@123456 | /employee |
| Técnico | tech.smith | Tech@123456 | /technician |
| Admin | admin.user | Admin@123456 | /admin |

## 3 Escenarios E2E Completos

### 1️⃣ Empleado Crea Ticket (~2 min)

**Archivo**: `test_employee_create_ticket.py`

```bash
pytest tests/e2e/test_employee_create_ticket.py -v --headed
```

**Flujo**:
1. Login como empleado (john.doe)
2. Click "Create Ticket"
3. Llenar título, descripción, prioridad
4. Submitir
5. Verificar ticket aparece en dashboard
6. Verificar SLA se calculó
7. Logout

**Assertions**: 7 tests validando cada paso

### 2️⃣ Técnico Resuelve Ticket (~3 min)

**Archivo**: `test_technician_resolve_ticket.py`

```bash
pytest tests/e2e/test_technician_resolve_ticket.py -v --headed
```

**Flujo**:
1. Login como técnico (tech.smith)
2. Ver cola de trabajo (unassigned)
3. Asignar ticket a sí mismo
4. Cambiar status a "In Progress"
5. Añadir comentarios
6. Resolver ticket
7. Verificar en "Resolved" tab
8. Logout

**Assertions**: 9 tests validando cada paso

### 3️⃣ Admin Ve Métricas (~3 min)

**Archivo**: `test_admin_dashboard_metrics.py`

```bash
pytest tests/e2e/test_admin_dashboard_metrics.py -v --headed
```

**Flujo**:
1. Login como admin (admin.user)
2. Ver dashboard con 6+ métricas
3. Verificar total, open, resolved, SLA compliance, avg resolution time
4. Verificar gráficos visibles
5. Ir a Reportes y exportar CSV
6. Ver log de auditoría
7. Ver gestión de usuarios
8. Logout

**Assertions**: 14 tests validando cada aspecto

## Markers (filtrar tests)

```bash
# Solo smoke tests (rápidos)
pytest tests/e2e/ -m smoke

# Solo tests lentos
pytest tests/e2e/ -m slow

# Solo tests E2E (todos)
pytest tests/e2e/ -m e2e
```

## Reportes

### HTML Report

```bash
pytest tests/e2e/ --html=tests/e2e/reports/report.html --self-contained-html
```

Abre automáticamente en navegador.

### JSON Report

```bash
pytest tests/e2e/ --json-report --json-report-file=tests/e2e/reports/report.json
```

### Allure Report

```bash
pip install allure-pytest
pytest tests/e2e/ --alluredir=tests/e2e/reports/allure
allure serve tests/e2e/reports/allure
```

## Artifacts Generados

Después de ejecutar tests:

```
tests/e2e/
├── reports/
│   ├── report.html           # Reporte HTML (abrir en navegador)
│   ├── report.json           # Reporte JSON
│   └── test_run.log          # Log detallado
├── screenshots/
│   └── fail_*.png            # Screenshots de fallos
└── videos/
    └── <test_names>          # Videos de cada test (si headless=false)
```

## Troubleshooting

### "Server not responding"

```bash
# Asegurar que TicketDesk está running
python app.py
# Verificar en http://localhost:5050
```

### "Login falló"

1. Verificar que servidor está en `/login`
2. Verificar credenciales en `conftest.py` TEST_USERS
3. Ejecutar con `--capture=no` para ver logs

### "Elemento no encontrado"

```bash
# Generar selector con codegen
playwright codegen http://localhost:5050

# Ejecutar test lentamente para inspeccionar
pytest tests/e2e/test_name.py --headed --slowmo=500
```

### Timeout

```bash
# Aumentar timeout global
pytest tests/e2e/ --timeout=300

# O en un test específico
page.set_default_timeout(60000)  # 60 segundos
```

## Best Practices

✅ **Usa data-testid** en HTML para selectores robustos  
✅ **Wait for element** antes de interactuar  
✅ **Describe assertions** claramente  
✅ **Use screenshots** para debugging  
✅ **Run headless** en CI/CD, `--headed` en desarrollo  

## Performance

- ⚡ **Smoke tests**: ~2 min (5 tests rápidos)
- 🐢 **Employee scenario**: ~2 min (7 tests)
- 🐢 **Technician scenario**: ~3 min (9 tests)
- 🐢 **Admin scenario**: ~3 min (14 tests)
- 🐢 **Todos**: ~10-12 min (30 tests)

## Ejemplo: Ejecutar una vez

```bash
# Setup
pip install -r tests/e2e/requirements-e2e.txt
playwright install chromium

# Asegurar servidor running
python app.py  # En otra terminal

# Ejecutar smoke tests
pytest tests/e2e/ -m smoke --headed

# Ver reporte
open tests/e2e/reports/report.html
```

## Monitorear CI/CD

Integrar en GitHub Actions, GitLab CI, Jenkins, etc:

```yaml
# .github/workflows/e2e.yml
- name: Run E2E Tests
  run: |
    pip install -r tests/e2e/requirements-e2e.txt
    playwright install chromium
    pytest tests/e2e/ --html=report.html
```

---

**Para documentación completa**: Ver `tests/e2e/README.md`

**Última actualización**: 2026-05-29
