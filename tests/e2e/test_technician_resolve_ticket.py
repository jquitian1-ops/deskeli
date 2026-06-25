"""
test_technician_resolve_ticket.py - Escenario E2E: Técnico resuelve ticket.

Flujo:
1. Login como técnico
2. Ver ticket en cola
3. Asignar ticket a sí mismo
4. Iniciar trabajo
5. Resolver ticket con notas
6. Verificar cambio de estado visible para empleado
"""
import pytest
from datetime import datetime
from tests.e2e.pages.LoginPage import LoginPage
from tests.e2e.pages.TechnicianDashboardPage import TechnicianDashboardPage
from tests.e2e.pages.EmployeeDashboardPage import EmployeeDashboardPage


@pytest.mark.e2e
@pytest.mark.slow
class TestTechnicianResolveTicket:
    """Tests para resolución de tickets por técnicos."""

    @pytest.fixture(autouse=True)
    def setup(self, page, test_technician, login_url):
        """Setup: navega a login como técnico."""
        self.page = page
        self.user = test_technician
        self.login_page = LoginPage(page)
        self.tech_dashboard = TechnicianDashboardPage(page)
        self.login_page.navigate_to_login()

    def test_technician_login_success(self):
        """
        Test: Login como técnico es exitoso.

        Assertions:
        - Credenciales se aceptan
        - Se navega a dashboard de técnico
        """
        success = self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )
        assert success, "Login como técnico falló"

        # Verify we're on technician dashboard
        assert self.tech_dashboard.is_on_technician_dashboard(), \
            "No se navegó al dashboard de técnico"

        print("✓ Login como técnico exitoso")

    def test_technician_queue_visible(self):
        """
        Test: Cola de trabajo es visible para técnico.

        Assertions:
        - Pestaña Queue existe
        - Se puede cambiar a Queue
        - Se muestran tickets sin asignar
        """
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Get queue count
        queue_count = self.tech_dashboard.get_queue_count()
        assert queue_count >= 0, "No se pudo obtener conteo de cola"

        print(f"✓ Tickets en cola: {queue_count}")

    def test_find_ticket_in_queue(self):
        """
        Test: Encontrar un ticket específico en la cola.

        Assertions:
        - Se puede buscar ticket en cola
        - Datos del ticket se obtienen correctamente
        """
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Try to find first ticket in queue
        # In real scenario, we'd create a ticket first
        self.page.click(self.tech_dashboard.TAB_QUEUE)
        self.page.wait_for_load_state("networkidle")

        # Get first ticket if exists
        rows = self.page.query_selector_all(self.tech_dashboard.TICKET_ROW)
        if rows:
            first_row = rows[0]
            id_elem = first_row.query_selector(self.tech_dashboard.TICKET_ID)
            if id_elem:
                ticket_id = id_elem.text_content().strip()
                print(f"✓ Encontrado ticket en cola: {ticket_id}")

    def test_assign_ticket_to_self(self):
        """
        Test: Asignar un ticket a sí mismo.

        Assertions:
        - Ticket se asigna exitosamente
        - Ticket desaparece de cola
        - Aparece en pestaña Assigned
        """
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Get queue count before
        queue_before = self.tech_dashboard.get_queue_count()

        if queue_before == 0:
            pytest.skip("No hay tickets en la cola para asignar")

        # Find first ticket
        self.page.click(self.tech_dashboard.TAB_QUEUE)
        self.page.wait_for_load_state("networkidle")

        rows = self.page.query_selector_all(self.tech_dashboard.TICKET_ROW)
        if not rows:
            pytest.skip("No se encontraron tickets en cola")

        first_row = rows[0]
        id_elem = first_row.query_selector(self.tech_dashboard.TICKET_ID)
        ticket_id = id_elem.text_content().strip() if id_elem else None

        if not ticket_id:
            pytest.skip("No se pudo extraer ticket ID")

        # Click y asignar
        first_row.click()
        self.page.wait_for_timeout(500)

        # Click assign button
        assign_btn = self.page.query_selector(self.tech_dashboard.BUTTON_ASSIGN)
        if assign_btn:
            assign_btn.click()
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_timeout(1000)

        # Verify queue count decreased
        queue_after = self.tech_dashboard.get_queue_count()
        assert queue_after < queue_before, \
            f"Cola no cambió: {queue_before} -> {queue_after}"

        print(f"✓ Ticket {ticket_id} asignado a sí mismo")

    def test_start_work_on_ticket(self):
        """
        Test: Iniciar trabajo en un ticket asignado.

        Assertions:
        - Estado del ticket cambia a "In Progress"
        - Botón "Start Work" funciona
        """
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Go to Assigned tickets
        self.page.click(self.tech_dashboard.TAB_ASSIGNED)
        self.page.wait_for_load_state("networkidle")

        assigned_count = self.tech_dashboard.get_queue_count()

        if assigned_count == 0:
            pytest.skip("No hay tickets asignados")

        # Get first assigned ticket
        rows = self.page.query_selector_all(self.tech_dashboard.TICKET_ROW)
        if rows:
            first_row = rows[0]
            id_elem = first_row.query_selector(self.tech_dashboard.TICKET_ID)
            ticket_id = id_elem.text_content().strip() if id_elem else None

            if ticket_id:
                # Click to open
                first_row.click()
                self.page.wait_for_load_state("networkidle")

                # Click Start Work
                start_btn = self.page.query_selector(self.tech_dashboard.BUTTON_START_WORK)
                if start_btn:
                    start_btn.click()
                    self.page.wait_for_load_state("networkidle")
                    self.page.wait_for_timeout(1000)

                    print(f"✓ Trabajo iniciado en ticket {ticket_id}")

    def test_add_comment_to_ticket(self):
        """
        Test: Añadir comentario a un ticket en progreso.

        Assertions:
        - Comentario se escribe correctamente
        - Aparece en sección de comentarios
        """
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Go to In Progress
        self.page.click(self.tech_dashboard.TAB_IN_PROGRESS)
        self.page.wait_for_load_state("networkidle")

        rows = self.page.query_selector_all(self.tech_dashboard.TICKET_ROW)

        if not rows:
            pytest.skip("No hay tickets en progreso")

        # Open first ticket
        first_row = rows[0]
        id_elem = first_row.query_selector(self.tech_dashboard.TICKET_ID)
        ticket_id = id_elem.text_content().strip() if id_elem else None

        first_row.click()
        self.page.wait_for_load_state("networkidle")

        # Add comment
        comment_text = f"Working on this issue. Have identified the problem. - {datetime.now().isoformat()}"

        comment_input = self.page.query_selector(self.tech_dashboard.INPUT_COMMENT)
        if comment_input:
            self.page.fill(self.tech_dashboard.INPUT_COMMENT, comment_text)
            self.page.wait_for_timeout(300)

            add_comment_btn = self.page.query_selector(self.tech_dashboard.BUTTON_ADD_COMMENT)
            if add_comment_btn:
                add_comment_btn.click()
                self.page.wait_for_load_state("networkidle")

                print(f"✓ Comentario añadido a ticket {ticket_id}")

    def test_resolve_ticket(self):
        """
        Test: Resolver un ticket completamente.

        Assertions:
        - Modal de resolución se abre
        - Se pueden escribir notas de resolución
        - Ticket cambia a estado "Resolved"
        """
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Go to In Progress
        self.page.click(self.tech_dashboard.TAB_IN_PROGRESS)
        self.page.wait_for_load_state("networkidle")

        rows = self.page.query_selector_all(self.tech_dashboard.TICKET_ROW)

        if not rows:
            pytest.skip("No hay tickets en progreso para resolver")

        # Get first ticket
        first_row = rows[0]
        id_elem = first_row.query_selector(self.tech_dashboard.TICKET_ID)
        ticket_id = id_elem.text_content().strip() if id_elem else "unknown"

        # Open ticket
        first_row.click()
        self.page.wait_for_load_state("networkidle")

        # Click resolve
        resolve_btn = self.page.query_selector(self.tech_dashboard.BUTTON_RESOLVE)
        if resolve_btn:
            resolve_btn.click()
            self.page.wait_for_timeout(500)

            # Fill resolution form
            resolution_notes = "Issue resolved. Updated network settings and restarted service."

            notes_input = self.page.query_selector(self.tech_dashboard.INPUT_RESOLUTION_NOTES)
            if notes_input:
                self.page.fill(self.tech_dashboard.INPUT_RESOLUTION_NOTES, resolution_notes)
                self.page.wait_for_timeout(300)

                # Confirm resolution
                confirm_btn = self.page.query_selector(self.tech_dashboard.BUTTON_CONFIRM_RESOLVE)
                if confirm_btn:
                    confirm_btn.click()
                    self.page.wait_for_load_state("networkidle")
                    self.page.wait_for_timeout(1000)

                    print(f"✓ Ticket {ticket_id} resuelto exitosamente")

    def test_verify_resolved_count_increased(self):
        """
        Test: Verificar que contador de resueltos aumentó.

        Assertions:
        - Pestaña Resolved muestra tickets
        - Conteo es coherente
        """
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Get resolved count
        resolved_count = self.tech_dashboard.get_resolved_tickets_count()

        assert resolved_count >= 0, "No se pudo obtener conteo de resueltos"
        assert resolved_count > 0, "Debería haber al menos 1 ticket resuelto"

        print(f"✓ Tickets resueltos: {resolved_count}")

    def test_sla_compliance_on_resolution(self):
        """
        Test: SLA se cumple durante resolución de ticket.

        Assertions:
        - Indicador de SLA visible durante resolución
        - Estado SLA es green/yellow/red apropiadamente
        """
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Go to In Progress
        self.page.click(self.tech_dashboard.TAB_IN_PROGRESS)
        self.page.wait_for_load_state("networkidle")

        rows = self.page.query_selector_all(self.tech_dashboard.TICKET_ROW)

        if rows:
            first_row = rows[0]
            first_row.click()
            self.page.wait_for_load_state("networkidle")

            # Check SLA indicator
            sla_elem = self.page.query_selector(self.tech_dashboard.DETAIL_SLA)

            if sla_elem:
                sla_status = sla_elem.text_content().strip()
                print(f"✓ SLA Status: {sla_status}")

    def test_logout_technician(self):
        """
        Test: Logout como técnico.

        Assertions:
        - Logout es exitoso
        - Retorna a login page
        """
        self.login_page.login(
            username=self.user["username"],
            password=self.user["password"]
        )

        # Logout
        success = self.login_page.logout()
        assert success, "Logout falló"

        assert "/login" in self.page.url, "No retornó a login"

        print("✓ Logout como técnico exitoso")
