"""
conftest.py - Fixtures y configuración global para E2E tests con Playwright.
Define setup/teardown de browser, usuarios de prueba, y variables globales.
"""
import pytest
import os
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext


# Configuración global
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:5050")
HEADLESS = os.getenv("TEST_HEADLESS", "false").lower() == "true"
SCREENSHOTS_DIR = Path("tests/e2e/screenshots")
VIDEOS_DIR = Path("tests/e2e/videos")
REPORTS_DIR = Path("tests/e2e/reports")


# Crear directorios si no existen
for dir_path in [SCREENSHOTS_DIR, VIDEOS_DIR, REPORTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# USUARIOS DE PRUEBA (MOCK)
# ==============================================================================
# En producción, estos deberían venir de LDAP/AD real
TEST_USERS = {
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


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(scope="session")
def browser_context_args():
    """
    Configuración de contexto de navegador.

    Returns:
        Dict con args para BrowserContext
    """
    return {
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "extra": {
            "base_url": BASE_URL
        }
    }


@pytest.fixture(scope="session")
def playwright_context_args(browser_context_args):
    """Configuración adicional de Playwright."""
    return {
        "ignore_https_errors": True,
    }


@pytest.fixture(scope="session")
def browser():
    """
    Crea instancia de navegador compartida para toda la sesión.

    Yields:
        playwright.sync_api.Browser
    """
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=HEADLESS,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu"
        ]
    )
    yield browser
    browser.close()
    playwright.stop()


@pytest.fixture
def context(browser):
    """
    Crea un contexto de navegador nuevo para cada test.

    Yields:
        playwright.sync_api.BrowserContext
    """
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 720},
        record_video_dir=str(VIDEOS_DIR),
        record_video_size={"width": 1280, "height": 720}
    )
    ctx.tracing.start(screenshots=True, snapshots=True)

    yield ctx

    # Guardar tracing
    trace_path = REPORTS_DIR / f"trace_{datetime.now().isoformat()}.zip"
    ctx.tracing.stop(path=str(trace_path))

    ctx.close()


@pytest.fixture
def page(context):
    """
    Crea una página nueva en el contexto.

    Yields:
        playwright.sync_api.Page
    """
    page = context.new_page()

    # Configurar timeouts
    page.set_default_timeout(30000)  # 30 segundos
    page.set_default_navigation_timeout(30000)

    # Event listeners para debugging
    page.on("console", lambda msg: print(f"[BROWSER CONSOLE] {msg.text}"))
    page.on("error", lambda error: print(f"[PAGE ERROR] {error}"))

    yield page

    # Screenshot en caso de fallo
    test_name = page.context.pages[0].url if page.context.pages else "unknown"

    page.close()


# ==============================================================================
# FIXTURES DE USUARIOS
# ==============================================================================

@pytest.fixture
def test_employee():
    """Retorna credenciales de usuario empleado."""
    return TEST_USERS["employee"].copy()


@pytest.fixture
def test_technician():
    """Retorna credenciales de usuario técnico."""
    return TEST_USERS["technician"].copy()


@pytest.fixture
def test_admin():
    """Retorna credenciales de usuario admin."""
    return TEST_USERS["admin"].copy()


@pytest.fixture
def test_users():
    """Retorna diccionario completo de usuarios de prueba."""
    return {k: v.copy() for k, v in TEST_USERS.items()}


# ==============================================================================
# FIXTURES DE URL
# ==============================================================================

@pytest.fixture
def base_url():
    """Retorna URL base de la aplicación."""
    return BASE_URL


@pytest.fixture
def login_url(base_url):
    """Retorna URL de login."""
    return f"{base_url}/login"


@pytest.fixture
def employee_portal_url(base_url):
    """Retorna URL del portal de empleados."""
    return f"{base_url}/employee"


@pytest.fixture
def technician_portal_url(base_url):
    """Retorna URL del portal de técnicos."""
    return f"{base_url}/technician"


@pytest.fixture
def admin_portal_url(base_url):
    """Retorna URL del portal de admin."""
    return f"{base_url}/admin"


# ==============================================================================
# HELPERS
# ==============================================================================

@pytest.fixture
def logged_in_employee_page(page, test_employee, login_url):
    """
    Retorna página con empleado ya logueado.

    Yields:
        Page logueada como empleado
    """
    page.goto(login_url)
    page.fill('input[name="username"]', test_employee["username"])
    page.fill('input[name="password"]', test_employee["password"])
    page.click('button:has-text("Login"), button:has-text("Ingresar")')
    page.wait_for_load_state("networkidle")

    yield page


@pytest.fixture
def logged_in_technician_page(page, test_technician, login_url):
    """
    Retorna página con técnico ya logueado.

    Yields:
        Page logueada como técnico
    """
    page.goto(login_url)
    page.fill('input[name="username"]', test_technician["username"])
    page.fill('input[name="password"]', test_technician["password"])
    page.click('button:has-text("Login"), button:has-text("Ingresar")')
    page.wait_for_load_state("networkidle")

    yield page


@pytest.fixture
def logged_in_admin_page(page, test_admin, login_url):
    """
    Retorna página con admin ya logueado.

    Yields:
        Page logueada como admin
    """
    page.goto(login_url)
    page.fill('input[name="username"]', test_admin["username"])
    page.fill('input[name="password"]', test_admin["password"])
    page.click('button:has-text("Login"), button:has-text("Ingresar")')
    page.wait_for_load_state("networkidle")

    yield page


# ==============================================================================
# HOOKS
# ==============================================================================

def pytest_configure(config):
    """Hook de configuración de pytest."""
    config.addinivalue_line(
        "markers", "e2e: marca tests como E2E tests"
    )
    config.addinivalue_line(
        "markers", "smoke: marca tests como smoke tests"
    )
    config.addinivalue_line(
        "markers", "slow: marca tests como lentos"
    )


def pytest_runtest_makereport(item, call):
    """Hook para capturar screenshot en fallos."""
    if call.excinfo is not None:
        # Test falló
        if hasattr(item, "funcargs"):
            page = item.funcargs.get("page")
            if page:
                timestamp = datetime.now().isoformat().replace(":", "-")
                screenshot_path = SCREENSHOTS_DIR / f"fail_{item.name}_{timestamp}.png"
                try:
                    page.screenshot(path=str(screenshot_path))
                    print(f"\nScreenshot guardado: {screenshot_path}")
                except Exception as e:
                    print(f"Error guardando screenshot: {e}")


# ==============================================================================
# UTILITIES
# ==============================================================================

def take_screenshot(page: Page, name: str):
    """
    Toma screenshot y lo guarda.

    Args:
        page: Página actual
        name: Nombre del screenshot
    """
    timestamp = datetime.now().isoformat().replace(":", "-")
    path = SCREENSHOTS_DIR / f"{name}_{timestamp}.png"
    page.screenshot(path=str(path))
    print(f"Screenshot: {path}")


def take_full_page_screenshot(page: Page, name: str):
    """
    Toma screenshot de página completa (incluye scroll).

    Args:
        page: Página actual
        name: Nombre del screenshot
    """
    timestamp = datetime.now().isoformat().replace(":", "-")
    path = SCREENSHOTS_DIR / f"{name}_full_{timestamp}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"Full page screenshot: {path}")


@pytest.fixture
def screenshot_helper(page):
    """Retorna función helper para screenshots."""
    return lambda name: take_screenshot(page, name)


@pytest.fixture
def full_screenshot_helper(page):
    """Retorna función helper para screenshots de página completa."""
    return lambda name: take_full_page_screenshot(page, name)
