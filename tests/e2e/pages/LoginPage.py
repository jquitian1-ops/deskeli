"""
LoginPage - Page Object Model para autenticación TicketDesk Enterprise.
Encapsula selectores y métodos para el flujo de login/logout.
"""
from playwright.sync_api import Page, expect
import time


class LoginPage:
    """Representa la página de login de TicketDesk."""

    # Selectores robustos
    INPUT_USERNAME = '[data-testid="username"], input[name="username"], input[type="text"]:first-of-type'
    INPUT_PASSWORD = '[data-testid="password"], input[name="password"], input[type="password"]'
    BUTTON_LOGIN = '[data-testid="login-button"], button:has-text("Login"), button:has-text("Ingresar"), button:has-text("Sign In")'
    BUTTON_LOGOUT = '[data-testid="logout-button"], button:has-text("Logout"), button:has-text("Cerrar Sesión")'
    TEXT_ERROR = '[data-testid="error-message"], .alert-danger, .error-message, p:has-text("Error")'
    NAVBAR_USER_MENU = '[data-testid="user-menu"], .navbar-user, button:has-text("Account")'

    # Roles/Portals
    PORTAL_EMPLOYEE = '[data-testid="portal-employee"], a:has-text("Employee"), a:has-text("Empleado")'
    PORTAL_TECHNICIAN = '[data-testid="portal-technician"], a:has-text("Technician"), a:has-text("Técnico")'
    PORTAL_ADMIN = '[data-testid="portal-admin"], a:has-text("Admin"), a:has-text("Administrador")'

    def __init__(self, page: Page):
        """Inicializa LoginPage con una referencia a la página."""
        self.page = page
        self.base_url = page.context.browser.new_context.__self__.extra.get(
            "base_url", "http://localhost:5050"
        )

    def navigate_to_login(self):
        """Navega a la página de login."""
        self.page.goto(f"{self.base_url}/login")
        # Esperar que cargue el form
        self.page.wait_for_load_state("networkidle")

    def login(self, username: str, password: str, wait_for_dashboard: bool = True) -> bool:
        """
        Realiza login con usuario y contraseña.

        Args:
            username: Usuario LDAP/AD
            password: Contraseña
            wait_for_dashboard: Si True, espera que cargue dashboard

        Returns:
            True si login fue exitoso, False en caso contrario
        """
        try:
            # Llenar campos
            self.page.fill(self.INPUT_USERNAME, username)
            self.page.fill(self.INPUT_PASSWORD, password)

            # Click login
            self.page.click(self.BUTTON_LOGIN)

            if wait_for_dashboard:
                # Esperar navegación post-login (3 segundos máximo)
                try:
                    self.page.wait_for_url(
                        lambda url: "/dashboard" in url or "/admin" in url or "/tickets" in url,
                        timeout=5000
                    )
                except Exception as e:
                    # Si falla navegación esperada, verificar si hay error visible
                    if self.page.query_selector(self.TEXT_ERROR):
                        return False

                self.page.wait_for_load_state("networkidle")

            return True
        except Exception as e:
            print(f"Error en login: {e}")
            return False

    def logout(self) -> bool:
        """
        Realiza logout y retorna a página de login.

        Returns:
            True si logout fue exitoso
        """
        try:
            # Abrir menú usuario si existe
            if self.page.query_selector(self.NAVBAR_USER_MENU):
                self.page.click(self.NAVBAR_USER_MENU)
                self.page.wait_for_timeout(500)

            # Click logout
            if self.page.query_selector(self.BUTTON_LOGOUT):
                self.page.click(self.BUTTON_LOGOUT)
                self.page.wait_for_url(
                    lambda url: "/login" in url,
                    timeout=5000
                )
                return True

            return False
        except Exception as e:
            print(f"Error en logout: {e}")
            return False

    def get_error_message(self) -> str:
        """
        Obtiene el mensaje de error si existe.

        Returns:
            Texto del error, o cadena vacía si no hay error
        """
        try:
            element = self.page.query_selector(self.TEXT_ERROR)
            if element:
                return element.text_content()
            return ""
        except Exception:
            return ""

    def is_logged_in(self) -> bool:
        """
        Verifica si usuario está logueado (no en página login).

        Returns:
            True si está logueado
        """
        return "/login" not in self.page.url

    def verify_login_form_visible(self) -> bool:
        """
        Verifica que formulario de login sea visible.

        Returns:
            True si username y password inputs existen
        """
        username_field = self.page.query_selector(self.INPUT_USERNAME)
        password_field = self.page.query_selector(self.INPUT_PASSWORD)
        login_btn = self.page.query_selector(self.BUTTON_LOGIN)

        return all([username_field, password_field, login_btn])

    def wait_for_portal_selection(self, timeout_ms: int = 5000):
        """
        Espera que aparezca selector de portal (si es necesario).

        Args:
            timeout_ms: Timeout en milisegundos
        """
        try:
            # Esperar que al menos uno de los portales sea visible
            self.page.wait_for_selector(
                f"{self.PORTAL_EMPLOYEE}, {self.PORTAL_TECHNICIAN}, {self.PORTAL_ADMIN}",
                timeout=timeout_ms
            )
        except Exception:
            pass

    def select_portal(self, portal_type: str) -> bool:
        """
        Selecciona un portal específico (Employee, Technician, Admin).

        Args:
            portal_type: "employee", "technician", o "admin"

        Returns:
            True si se seleccionó exitosamente
        """
        portal_map = {
            "employee": self.PORTAL_EMPLOYEE,
            "technician": self.PORTAL_TECHNICIAN,
            "admin": self.PORTAL_ADMIN
        }

        selector = portal_map.get(portal_type.lower())
        if not selector:
            return False

        try:
            self.page.click(selector)
            self.page.wait_for_load_state("networkidle")
            return True
        except Exception:
            return False
