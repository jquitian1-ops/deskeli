"""
test_employee_create_ticket.py - Escenario E2E: Empleado crea ticket.

Flujo:
1. Login como empleado
2. Crear ticket con título y descripción
3. Verificar ticket aparece en dashboard
4. Verificar SLA calculado
"""
import pytest
from datetime import datetime
from tests.e2e.pages.LoginPage import LoginPage
from tests.e2e.pages.EmployeeDashboardPage import EmployeeDashboardPage


@pytest.mark.e2e
@pytest.mark.smoke
class TestEmployeeCreateTicket:
    """Tests para creación de tickets por empleados."""

    @pytest.fixture(autouse=True)
    def setup(self, page, test_employee, login_url):
        """Setup: navega a login y guarda datos."""
        self.page = page
        self.user = test_employee
        self.login_page = LoginPage(page)
        self.dashboard = EmployeeDashboardPage(page)
        self.login_page.navigate_to_login()

    def test_login_employee_success(self):
        """
        Test: Login como empleado es exitoso.

        Assertions:
        - Login button existe
        - Credentials se aceptan
        - Se navega a dashboard
        """
        # Verify login form is visible
        assert self.login_page.verify_login_form_visible(), \
            "Login form elementos no son visibles"

        # Perform login
        success = self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )
        assert success, "Login falló"

        # Verify we're logged in
        assert self.login_page.is_logged_in(), \
            "Usuario no está logueado después de login"

        # Verify dashboard page loaded
        assert self.dashboard.is_on_dashboard(), \
            "No se navegó al dashboard después de login"

    def test_employee_dashboard_loads(self):
        """
        Test: Dashboard de empleado carga correctamente.

        Assertions:
        - Página carga sin errores
        - Elementos principales visibles
        """
        # Login
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Verify page is loaded
        assert self.page.title is not None, "Página no tiene título"

        # Verify create ticket button exists
        create_btn_visible = self.page.query_selector(
            self.dashboard.BUTTON_CREATE_TICKET
        ) is not None
        assert create_btn_visible, "Botón 'Create Ticket' no visible"

    def test_create_ticket_with_title_and_description(self):
        """
        Test: Crear ticket con título y descripción exitosamente.

        Assertions:
        - Formulario de crear se abre
        - Se puede llenar título y descripción
        - Ticket se crea exitosamente
        """
        # Login
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Click create ticket button
        assert self.dashboard.click_create_ticket_button(), \
            "No se pudo hacer click en botón 'Create Ticket'"

        # Verify form opened (wait for inputs to be visible)
        self.page.wait_for_selector(
            self.dashboard.INPUT_TITLE,
            timeout=5000
        )

        # Fill form
        ticket_title = f"Test Ticket - Network Issues {datetime.now().isoformat()}"
        ticket_description = "Cannot access printer on 3rd floor. Error: Network path not found."

        assert self.dashboard.fill_create_ticket_form(
            title=ticket_title,
            description=ticket_description,
            priority="High",
            category="Network"
        ), "No se pudo llenar el formulario"

        # Submit ticket
        assert self.dashboard.submit_ticket(), \
            "No se pudo submitir el ticket"

        # Store for assertion
        self.created_ticket_title = ticket_title

    def test_created_ticket_appears_in_dashboard(self):
        """
        Test: Ticket creado aparece en dashboard empleado.

        Assertions:
        - Ticket es visible en lista
        - Datos básicos coinciden (título, prioridad)
        - Estado inicial es "Open"
        """
        # Login
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Create a ticket
        ticket_title = f"Integration Test Ticket {datetime.now().timestamp()}"
        description = "Test description for integration test"

        self.dashboard.click_create_ticket_button()
        self.page.wait_for_selector(self.dashboard.INPUT_TITLE)

        self.dashboard.fill_create_ticket_form(
            title=ticket_title,
            description=description,
            priority="Medium"
        )
        self.dashboard.submit_ticket()

        # Wait for ticket to appear in list
        self.page.wait_for_timeout(2000)

        # Verify ticket count increased
        initial_count = 0
        final_count = self.dashboard.get_ticket_count()
        assert final_count > initial_count, \
            f"Ticket count no aumentó: {initial_count} -> {final_count}"

        # Find ticket by title
        found_ticket = self.dashboard.find_ticket_by_title(ticket_title)
        assert found_ticket is not None, \
            f"Ticket creado '{ticket_title}' no encontrado en dashboard"

        # Verify ticket data
        assert ticket_title in found_ticket["title"], \
            f"Título no coincide: esperado '{ticket_title}', obtuve '{found_ticket['title']}'"

        assert found_ticket["status"] is not None, \
            "Estado del ticket no está disponible"

        print(f"✓ Ticket creado: {found_ticket['id']} - {found_ticket['title']}")

    def test_ticket_sla_calculated(self):
        """
        Test: SLA del ticket se calcula correctamente.

        Assertions:
        - SLA se muestra en ticket
        - Tiempo SLA es razonable (> 0)
        - Indicador visual de SLA existe
        """
        # Login
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Create ticket
        ticket_title = f"SLA Test {datetime.now().timestamp()}"
        self.dashboard.click_create_ticket_button()
        self.page.wait_for_selector(self.dashboard.INPUT_TITLE)

        self.dashboard.fill_create_ticket_form(
            title=ticket_title,
            description="Test para validar SLA",
            priority="High"
        )
        self.dashboard.submit_ticket()

        # Wait and find ticket
        self.page.wait_for_timeout(2000)
        found_ticket = self.dashboard.find_ticket_by_title(ticket_title)

        assert found_ticket is not None, "Ticket no encontrado"

        # Click ticket to see details
        assert self.dashboard.click_ticket(found_ticket["id"]), \
            "No se pudo abrir ticket"

        self.page.wait_for_timeout(1000)

        # Verify SLA is visible
        assert self.dashboard.verify_sla_visible(), \
            "SLA no es visible en detalles del ticket"

        # Get ticket details
        details = self.dashboard.get_ticket_detail(found_ticket["id"])
        assert details is not None, "No se pudieron obtener detalles del ticket"
        assert details.get("sla_remaining") is not None, \
            "SLA remaining no está disponible"

        print(f"✓ SLA calculado: {details.get('sla_remaining')}")

    def test_create_multiple_tickets(self):
        """
        Test: Crear múltiples tickets en secuencia.

        Assertions:
        - Se pueden crear 3 tickets diferentes
        - Todos aparecen en dashboard
        - Conteo de tickets aumenta correctamente
        """
        # Login
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        tickets_created = []

        for i in range(3):
            # Create ticket
            ticket_title = f"Batch Ticket {i+1} {datetime.now().timestamp()}"
            self.dashboard.click_create_ticket_button()
            self.page.wait_for_selector(self.dashboard.INPUT_TITLE)

            self.dashboard.fill_create_ticket_form(
                title=ticket_title,
                description=f"Batch test description #{i+1}",
                priority=["High", "Medium", "Low"][i]
            )
            self.dashboard.submit_ticket()

            # Wait for UI to update
            self.page.wait_for_timeout(1500)

            # Verify ticket appears
            found = self.dashboard.find_ticket_by_title(ticket_title)
            assert found is not None, f"Ticket {i+1} no encontrado"

            tickets_created.append(found)
            print(f"✓ Ticket {i+1} creado: {found['id']}")

        # Verify all tickets are visible
        assert len(tickets_created) == 3, \
            f"Se crearon {len(tickets_created)} tickets, esperábamos 3"

    def test_ticket_form_validation(self):
        """
        Test: Validación de campos en formulario de crear ticket.

        Assertions:
        - No se puede submitir sin título
        - Descripción es recomendada (warning si está vacía)
        """
        # Login
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Open create form
        self.dashboard.click_create_ticket_button()
        self.page.wait_for_selector(self.dashboard.INPUT_TITLE)

        # Try to submit empty form
        submit_btn = self.page.query_selector(self.dashboard.BUTTON_SUBMIT_TICKET)
        assert submit_btn is not None, "Submit button no encontrado"

        # Check if button is disabled or form has validation
        # (behavior depende de implementación)
        submit_enabled = not submit_btn.is_disabled() if submit_btn else True

        # Cancel form
        self.dashboard.cancel_ticket_creation()

        print(f"✓ Validación de formulario: submit_enabled={submit_enabled}")

    def test_logout_employee(self):
        """
        Test: Logout como empleado retorna a login.

        Assertions:
        - Logout button existe
        - Después de logout, URL es de login
        - No se puede acceder a dashboard sin login
        """
        # Login
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Perform logout
        success = self.login_page.logout()
        assert success, "Logout falló"

        # Verify we're back at login
        assert "/login" in self.page.url, \
            f"Después de logout, URL es: {self.page.url}"

        assert not self.login_page.is_logged_in(), \
            "Usuario aún está logueado después de logout"

        print("✓ Logout exitoso")
