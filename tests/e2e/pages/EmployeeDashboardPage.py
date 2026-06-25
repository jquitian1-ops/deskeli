"""
EmployeeDashboardPage - Page Object Model para portal de empleados.
Encapsula creación de tickets, visualización de estado y SLA.
"""
from playwright.sync_api import Page
from typing import Optional, Dict


class EmployeeDashboardPage:
    """Representa el dashboard de empleados."""

    # Selectores para navegación
    BUTTON_CREATE_TICKET = '[data-testid="create-ticket-button"], button:has-text("Create Ticket"), button:has-text("Crear Ticket"), a:has-text("New Ticket")'
    TAB_MY_TICKETS = '[data-testid="tab-my-tickets"], button:has-text("My Tickets"), button:has-text("Mis Tickets")'
    TAB_OPEN_TICKETS = '[data-testid="tab-open-tickets"], button:has-text("Open")'
    TAB_CLOSED_TICKETS = '[data-testid="tab-closed-tickets"], button:has-text("Closed")'

    # Selectores para formulario de crear ticket
    INPUT_TITLE = '[data-testid="ticket-title"], input[name="title"], textarea[placeholder*="Title"]'
    INPUT_DESCRIPTION = '[data-testid="ticket-description"], textarea[name="description"], textarea[placeholder*="Description"]'
    SELECT_PRIORITY = '[data-testid="ticket-priority"], select[name="priority"], [role="combobox"]'
    SELECT_CATEGORY = '[data-testid="ticket-category"], select[name="category"], [role="combobox"]'
    BUTTON_SUBMIT_TICKET = '[data-testid="submit-ticket"], button:has-text("Create"), button:has-text("Crear"), button:has-text("Submit")'
    BUTTON_CANCEL = '[data-testid="cancel-button"], button:has-text("Cancel"), button:has-text("Cancelar")'

    # Selectores para lista de tickets
    TICKET_ROW = '[data-testid="ticket-row"], tr:has([data-testid="ticket-id"]), .ticket-card, .ticket-item'
    TICKET_ID = '[data-testid="ticket-id"], .ticket-id, span:has-text("#")'
    TICKET_TITLE = '[data-testid="ticket-title"], .ticket-title, .ticket-subject'
    TICKET_STATUS = '[data-testid="ticket-status"], .ticket-status, span.badge'
    TICKET_SLA = '[data-testid="ticket-sla"], .ticket-sla, .sla-indicator'
    TICKET_PRIORITY = '[data-testid="ticket-priority"], .ticket-priority, span.priority'

    # Selectores para detalles
    TICKET_DETAIL_PANEL = '[data-testid="ticket-detail"], .ticket-detail, .detail-panel'
    TICKET_DETAIL_STATUS = '[data-testid="detail-status"], .detail-status'
    TICKET_DETAIL_ASSIGNEE = '[data-testid="detail-assignee"], .detail-assignee'
    TICKET_DETAIL_COMMENTS = '[data-testid="detail-comments"], .comments-section, .conversation'

    # Selectores para SLA
    SLA_PROGRESS_BAR = '[data-testid="sla-progress"], .sla-progress, .progress'
    SLA_TIME_REMAINING = '[data-testid="sla-time"], .sla-time, .remaining-time'

    def __init__(self, page: Page):
        """Inicializa EmployeeDashboardPage con referencia a página."""
        self.page = page

    def is_on_dashboard(self) -> bool:
        """
        Verifica si estamos en dashboard de empleado.

        Returns:
            True si URL contiene /employee o /dashboard
        """
        return "/employee" in self.page.url or "/dashboard" in self.page.url

    def click_create_ticket_button(self) -> bool:
        """
        Click en botón crear ticket.

        Returns:
            True si botón fue clickeado
        """
        try:
            self.page.click(self.BUTTON_CREATE_TICKET)
            self.page.wait_for_load_state("networkidle")
            return True
        except Exception as e:
            print(f"Error clicking create ticket: {e}")
            return False

    def fill_create_ticket_form(
        self,
        title: str,
        description: str,
        priority: Optional[str] = None,
        category: Optional[str] = None
    ) -> bool:
        """
        Llena formulario de crear ticket.

        Args:
            title: Título del ticket
            description: Descripción del problema
            priority: Prioridad (High, Medium, Low) - opcional
            category: Categoría (Network, Hardware, etc) - opcional

        Returns:
            True si formulario fue llenado exitosamente
        """
        try:
            # Llenar título
            self.page.fill(self.INPUT_TITLE, title)
            self.page.wait_for_timeout(300)

            # Llenar descripción
            self.page.fill(self.INPUT_DESCRIPTION, description)
            self.page.wait_for_timeout(300)

            # Seleccionar prioridad si se proporciona
            if priority:
                try:
                    select = self.page.query_selector(self.SELECT_PRIORITY)
                    if select:
                        self.page.select_option(self.SELECT_PRIORITY, priority)
                        self.page.wait_for_timeout(200)
                except Exception:
                    # Si no es un select, intentar click en opción
                    self.page.click(f"text={priority}")
                    self.page.wait_for_timeout(200)

            # Seleccionar categoría si se proporciona
            if category:
                try:
                    select = self.page.query_selector(self.SELECT_CATEGORY)
                    if select:
                        self.page.select_option(self.SELECT_CATEGORY, category)
                        self.page.wait_for_timeout(200)
                except Exception:
                    self.page.click(f"text={category}")
                    self.page.wait_for_timeout(200)

            return True
        except Exception as e:
            print(f"Error llenando formulario: {e}")
            return False

    def submit_ticket(self) -> bool:
        """
        Submite el formulario de crear ticket.

        Returns:
            True si ticket fue creado exitosamente
        """
        try:
            self.page.click(self.BUTTON_SUBMIT_TICKET)
            # Esperar confirmación o redirección
            self.page.wait_for_load_state("networkidle")
            # Esperar que desaparezca el formulario o modal
            self.page.wait_for_timeout(1000)
            return True
        except Exception as e:
            print(f"Error submitiendo ticket: {e}")
            return False

    def cancel_ticket_creation(self) -> bool:
        """
        Cancela creación de ticket.

        Returns:
            True si operación fue exitosa
        """
        try:
            self.page.click(self.BUTTON_CANCEL)
            self.page.wait_for_load_state("networkidle")
            return True
        except Exception:
            return False

    def get_ticket_count(self) -> int:
        """
        Obtiene cantidad de tickets visibles en lista.

        Returns:
            Número de tickets en la tabla
        """
        try:
            rows = self.page.query_selector_all(self.TICKET_ROW)
            return len(rows)
        except Exception:
            return 0

    def find_ticket_by_title(self, title: str) -> Optional[Dict]:
        """
        Busca ticket por título en la lista.

        Args:
            title: Título a buscar

        Returns:
            Dict con datos del ticket, o None si no encontrado
        """
        try:
            rows = self.page.query_selector_all(self.TICKET_ROW)
            for row in rows:
                title_elem = row.query_selector(self.TICKET_TITLE)
                if title_elem and title.lower() in title_elem.text_content().lower():
                    # Extraer datos
                    id_elem = row.query_selector(self.TICKET_ID)
                    status_elem = row.query_selector(self.TICKET_STATUS)
                    priority_elem = row.query_selector(self.TICKET_PRIORITY)

                    return {
                        "id": id_elem.text_content().strip() if id_elem else None,
                        "title": title_elem.text_content().strip(),
                        "status": status_elem.text_content().strip() if status_elem else None,
                        "priority": priority_elem.text_content().strip() if priority_elem else None,
                        "element": row
                    }
            return None
        except Exception as e:
            print(f"Error buscando ticket: {e}")
            return None

    def click_ticket(self, ticket_id: str) -> bool:
        """
        Click en un ticket específico por ID.

        Args:
            ticket_id: ID del ticket (ej. "#1001")

        Returns:
            True si ticket fue abierto
        """
        try:
            # Buscar row con ese ID
            rows = self.page.query_selector_all(self.TICKET_ROW)
            for row in rows:
                id_elem = row.query_selector(self.TICKET_ID)
                if id_elem and ticket_id in id_elem.text_content():
                    row.click()
                    self.page.wait_for_load_state("networkidle")
                    return True
            return False
        except Exception:
            return False

    def get_ticket_detail(self, ticket_id: str) -> Optional[Dict]:
        """
        Obtiene detalles completos de un ticket abierto.

        Args:
            ticket_id: ID del ticket

        Returns:
            Dict con detalles (status, assignee, SLA, etc)
        """
        try:
            detail_panel = self.page.query_selector(self.TICKET_DETAIL_PANEL)
            if not detail_panel:
                return None

            status_elem = detail_panel.query_selector(self.TICKET_DETAIL_STATUS)
            assignee_elem = detail_panel.query_selector(self.TICKET_DETAIL_ASSIGNEE)
            sla_elem = detail_panel.query_selector(self.SLA_TIME_REMAINING)

            return {
                "ticket_id": ticket_id,
                "status": status_elem.text_content().strip() if status_elem else None,
                "assignee": assignee_elem.text_content().strip() if assignee_elem else None,
                "sla_remaining": sla_elem.text_content().strip() if sla_elem else None,
            }
        except Exception as e:
            print(f"Error obteniendo detalles: {e}")
            return None

    def verify_sla_visible(self) -> bool:
        """
        Verifica que indicador de SLA sea visible.

        Returns:
            True si SLA está visible en tickets
        """
        try:
            sla_elements = self.page.query_selector_all(self.TICKET_SLA)
            return len(sla_elements) > 0
        except Exception:
            return False

    def switch_to_open_tickets(self) -> bool:
        """
        Cambia a pestaña de tickets abiertos.

        Returns:
            True si cambio fue exitoso
        """
        try:
            self.page.click(self.TAB_OPEN_TICKETS)
            self.page.wait_for_load_state("networkidle")
            return True
        except Exception:
            return False

    def switch_to_closed_tickets(self) -> bool:
        """
        Cambia a pestaña de tickets cerrados.

        Returns:
            True si cambio fue exitoso
        """
        try:
            self.page.click(self.TAB_CLOSED_TICKETS)
            self.page.wait_for_load_state("networkidle")
            return True
        except Exception:
            return False
