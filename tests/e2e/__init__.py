"""
TicketDesk Enterprise E2E Tests

Tests end-to-end (E2E) con Playwright para validar flujos completos:
- Login y autenticación
- Creación de tickets por empleados
- Resolución de tickets por técnicos
- Dashboards y métricas para administradores
- Auditoría y logging

Para ejecutar:
    pytest tests/e2e/ -v --headed
    pytest tests/e2e/ -m smoke  # Solo smoke tests
    pytest tests/e2e/test_employee_create_ticket.py -v  # Archivo específico

Para generar reporte HTML:
    pytest tests/e2e/ --html=tests/e2e/reports/report.html --self-contained-html

Requisitos:
    pip install -r tests/e2e/requirements-e2e.txt
    playwright install

Variables de entorno (.env):
    TEST_BASE_URL=http://localhost:5050  # URL base de la aplicación
    TEST_HEADLESS=true                   # false para ver browser
"""
