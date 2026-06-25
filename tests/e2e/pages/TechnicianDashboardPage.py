"""
TechnicianDashboardPage - Page Object Model para portal de técnicos.
Encapsula gestión de cola de trabajo, asignación y resolución de tickets.
"""
from playwright.sync_api import Page
from typing import Optional, Dict, List


class TechnicianDashboardPage:
    """Representa el dashboard de técnicos."""

    # Selectores principales
    TAB_QUEUE = '[data-testid="tab-queue"], button:has-text("Queue"), button:has-text("Cola")'
    TAB_ASSIGNED = '[data-testid="tab-assigned"], button:has-text("Assigned"), button:has-text("Asignados")'
    TAB_IN_PROGRESS = '[data-testid="tab-in-progress"], button:has-text("In Progress"), button:has-text("En Progreso")'
    TAB_RESOLVED = '[data-testid="tab-resolved"], button:has-text("Resolved"), button:has-text("Resueltos")'

    # Selectores para lista de tickets
    TICKET_ROW = '[data-testid="ticket-row"], tr:has([data-testid="ticket-id"]), .ticket-card, .queue-item'
    TICKET_ID = '[data-testid="ticket-id"], .ticket-id'
    TICKET_TITLE = '[data-testid="ticket-title"], .ticket-title, .ticket-subject'
    TICKET_PRIORITY = '[data-testid="ticket-priority"], .ticket-priority, .priority-badge'
    TICKET_STATUS = '[data-testid="ticket-status"], .ticket-status'
    TICKET_REQUESTER = '[data-testid="ticket-requester"], .requester-name, .submitted-by'

    # Selectores para acciones en ticket
    BUTTON_ASSIGN = '[data-testid="assign-button"], button:has-text("Assign"), button:has-text("Asignar")'
    BUTTON_START_WORK = '[data-testid="start-work"], button:has-text("Start"), button:has-text("Iniciar")'
    BUTTON_RESOLVE = '[data-testid="resolve-button"], button:has-text("Resolve"), button:has-text("Resolver")'
    BUTTON_REOPEN = '[data-testid="reopen-button"], button:has-text("Reopen"), button:has-text("Reabrir")'

    # Selectores para panel de detalles
    DETAIL_PANEL = '[data-testid="ticket-detail"], .ticket-detail, .detail-section'
    DETAIL_STATUS = '[data-testid="detail-status"], .status-field'
    DETAIL_ASSIGNEE = '[data-testid="detail-assignee"], .assignee-field'
    DETAIL_TIME_SPENT = '[data-testid="time-spent"], .time-spent, .work-log'
    DETAIL_SLA = '[data-testid="sla-status"], .sla-status'

    # Selectores para resolución
    MODAL_RESOLVE = '[data-testid="resolve-modal"], .modal, dialog:has-text("Resolve")'
    INPUT_RESOLUTION_NOTES = '[data-testid="resolution-notes"], textarea[name="resolution"], textarea[placeholder*="Resolution"]'
    SELECT_RESOLUTION_CATEGORY = '[data-testid="resolution-category"], select[name="category"]'
    BUTTON_CONFIRM_RESOLVE = '[data-testid="confirm-resolve"], button:has-text("Resolve"), button:has-text("Resolver")'

    # Selectores para comentarios
    COMMENT_SECTION = '[data-testid="comments"], .comments, .conversation'
    INPUT_COMMENT = '[data-testid="comment-input"], textarea[name="comment"], input[placeholder*="Add comment"]'
    BUTTON_ADD_COMMENT = '[data-testid="add-comment"], button:has-text("Comment"), button:has-text("Comentar")'

    # Selectores para SLA
    SLA_PROGRESS = '[data-testid="sla-progress"], .sla-progress, .progress-bar'
    SLA_TIME = '[data-testid="sla-time"], .sla-time-remaining'

    # Selectores para asignación
    MODAL_ASSIGN = '[data-testid="assign-modal"], .modal, dialog:has-text("Assign")'
    SELECT_ASSIGNEE = '[data-testid="assignee-select"], select[name="assignee"], [role="combobox"]'
    BUTTON_CONFIRM_ASSIGN = '[data-testid="confirm-assign"], button:has-text("Assign"), button:has-text("Asignar")'

    def __init__(self, page: Page):
        """Inicializa TechnicianDashboardPage con referencia a página."""
        self.page = page

    def is_on_technician_dashboard(self) -> bool:
        """
        Verifica si estamos en dashboard de técnico.

        Returns:
            True si URL contiene /technician o /tech
        """
        return "/technician" in self.page.url or "/tech" in self.page.url

    def get_queue_count(self) -> int:
        """
        Obtiene cantidad de tickets en cola.

        Returns:
            Número de tickets unassigned
        """
        try:
            self.page.click(self.TAB_QUEUE)
            self.page.wait_for_load_state("networkidle")
            rows = self.page.query_selector_all(self.TICKET_ROW)
            return len(rows)
        except Exception:
            return 0

    def find_ticket_in_queue(self, ticket_id: str) -> Optional[Dict]:
        """
        Busca ticket específico en cola.

        Args:
            ticket_id: ID del ticket (ej. "1001")

        Returns:
            Dict con datos del ticket, o None
        """
        try:
            self.page.click(self.TAB_QUEUE)
            self.page.wait_for_load_state("networkidle")

            rows = self.page.query_selector_all(self.TICKET_ROW)
            for row in rows:
                id_elem = row.query_selector(self.TICKET_ID)
                if id_elem and ticket_id in id_elem.text_content():
                    title_elem = row.query_selector(self.TICKET_TITLE)
                    priority_elem = row.query_selector(self.TICKET_PRIORITY)
                    requester_elem = row.query_selector(self.TICKET_REQUESTER)

                    return {
                        "id": id_elem.text_content().strip(),
                        "title": title_elem.text_content().strip() if title_elem else None,
                        "priority": priority_elem.text_content().strip() if priority_elem else None,
                        "requester": requester_elem.text_content().strip() if requester_elem else None,
                        "element": row
                    }
            return None
        except Exception as e:
            print(f"Error buscando ticket en cola: {e}")
            return None

    def assign_ticket_to_self(self, ticket_id: str) -> bool:
        """
        Asigna un ticket a sí mismo.

        Args:
            ticket_id: ID del ticket

        Returns:
            True si asignación fue exitosa
        """
        try:
            # Encontrar y clickear ticket
            ticket = self.find_ticket_in_queue(ticket_id)
            if not ticket:
                return False

            ticket["element"].click()
            self.page.wait_for_load_state("networkidle")

            # Click assign
            self.page.click(self.BUTTON_ASSIGN)
            self.page.wait_for_timeout(500)

            # Confirmar asignación (buscar botón confirmar o seleccionar "Me")
            try:
                # Si hay modal de asignación
                modal = self.page.query_selector(self.MODAL_ASSIGN)
                if modal:
                    # Click en "Assign to me" o similar
                    confirm_btn = modal.query_selector(self.BUTTON_CONFIRM_ASSIGN)
                    if confirm_btn:
                        confirm_btn.click()
                        self.page.wait_for_load_state("networkidle")
                        return True
            except Exception:
                pass

            return True
        except Exception as e:
            print(f"Error asignando ticket: {e}")
            return False

    def start_working_on_ticket(self, ticket_id: str) -> bool:
        """
        Inicia trabajo en un ticket asignado.

        Args:
            ticket_id: ID del ticket

        Returns:
            True si operación fue exitosa
        """
        try:
            # Ir a pestaña asignados
            self.page.click(self.TAB_ASSIGNED)
            self.page.wait_for_load_state("networkidle")

            # Buscar ticket
            rows = self.page.query_selector_all(self.TICKET_ROW)
            for row in rows:
                id_elem = row.query_selector(self.TICKET_ID)
                if id_elem and ticket_id in id_elem.text_content():
                    row.click()
                    self.page.wait_for_load_state("networkidle")

                    # Click start work
                    self.page.click(self.BUTTON_START_WORK)
                    self.page.wait_for_load_state("networkidle")
                    return True

            return False
        except Exception as e:
            print(f"Error iniciando trabajo: {e}")
            return False

    def add_comment(self, ticket_id: str, comment_text: str) -> bool:
        """
        Añade comentario a un ticket.

        Args:
            ticket_id: ID del ticket
            comment_text: Texto del comentario

        Returns:
            True si comentario fue añadido
        """
        try:
            # Encontrar y abrir ticket
            self.page.click(self.TAB_IN_PROGRESS)
            self.page.wait_for_load_state("networkidle")

            rows = self.page.query_selector_all(self.TICKET_ROW)
            for row in rows:
                id_elem = row.query_selector(self.TICKET_ID)
                if id_elem and ticket_id in id_elem.text_content():
                    row.click()
                    self.page.wait_for_load_state("networkidle")

                    # Llenar comentario
                    self.page.fill(self.INPUT_COMMENT, comment_text)
                    self.page.wait_for_timeout(300)

                    # Submitir
                    self.page.click(self.BUTTON_ADD_COMMENT)
                    self.page.wait_for_load_state("networkidle")
                    return True

            return False
        except Exception as e:
            print(f"Error añadiendo comentario: {e}")
            return False

    def resolve_ticket(
        self,
        ticket_id: str,
        resolution_notes: str,
        resolution_category: Optional[str] = None
    ) -> bool:
        """
        Resuelve un ticket en progreso.

        Args:
            ticket_id: ID del ticket
            resolution_notes: Notas de resolución
            resolution_category: Categoría de resolución (opcional)

        Returns:
            True si ticket fue resuelto
        """
        try:
            # Encontrar ticket en "In Progress"
            self.page.click(self.TAB_IN_PROGRESS)
            self.page.wait_for_load_state("networkidle")

            rows = self.page.query_selector_all(self.TICKET_ROW)
            found = False
            for row in rows:
                id_elem = row.query_selector(self.TICKET_ID)
                if id_elem and ticket_id in id_elem.text_content():
                    row.click()
                    self.page.wait_for_load_state("networkidle")
                    found = True
                    break

            if not found:
                return False

            # Click resolve
            self.page.click(self.BUTTON_RESOLVE)
            self.page.wait_for_timeout(500)

            # Llenar modal de resolución
            modal = self.page.query_selector(self.MODAL_RESOLVE)
            if modal:
                # Llenar notas
                self.page.fill(self.INPUT_RESOLUTION_NOTES, resolution_notes)
                self.page.wait_for_timeout(300)

                # Seleccionar categoría si se proporciona
                if resolution_category:
                    try:
                        self.page.select_option(self.SELECT_RESOLUTION_CATEGORY, resolution_category)
                        self.page.wait_for_timeout(200)
                    except Exception:
                        pass

                # Confirmar
                self.page.click(self.BUTTON_CONFIRM_RESOLVE)
                self.page.wait_for_load_state("networkidle")
                return True

            return False
        except Exception as e:
            print(f"Error resolviendo ticket: {e}")
            return False

    def get_ticket_detail(self) -> Optional[Dict]:
        """
        Obtiene detalles del ticket actualmente abierto.

        Returns:
            Dict con estado, asignado, tiempo, SLA, etc
        """
        try:
            detail = self.page.query_selector(self.DETAIL_PANEL)
            if not detail:
                return None

            status_elem = detail.query_selector(self.DETAIL_STATUS)
            assignee_elem = detail.query_selector(self.DETAIL_ASSIGNEE)
            time_elem = detail.query_selector(self.DETAIL_TIME_SPENT)
            sla_elem = detail.query_selector(self.DETAIL_SLA)

            return {
                "status": status_elem.text_content().strip() if status_elem else None,
                "assignee": assignee_elem.text_content().strip() if assignee_elem else None,
                "time_spent": time_elem.text_content().strip() if time_elem else None,
                "sla": sla_elem.text_content().strip() if sla_elem else None,
            }
        except Exception:
            return None

    def verify_ticket_status(self, expected_status: str) -> bool:
        """
        Verifica que el ticket actual tenga el estado esperado.

        Args:
            expected_status: Estado esperado (Open, In Progress, Resolved, etc)

        Returns:
            True si estado coincide
        """
        try:
            detail = self.get_ticket_detail()
            if detail and detail.get("status"):
                return expected_status.lower() in detail["status"].lower()
            return False
        except Exception:
            return False

    def get_resolved_tickets_count(self) -> int:
        """
        Obtiene cantidad de tickets resueltos por este técnico.

        Returns:
            Número de tickets resueltos
        """
        try:
            self.page.click(self.TAB_RESOLVED)
            self.page.wait_for_load_state("networkidle")
            rows = self.page.query_selector_all(self.TICKET_ROW)
            return len(rows)
        except Exception:
            return 0
