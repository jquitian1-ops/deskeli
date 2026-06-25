"""
AdminDashboardPage - Page Object Model para portal de administrador.
Encapsula dashboards, reportes y configuración.
"""
from playwright.sync_api import Page
from typing import Optional, Dict, List


class AdminDashboardPage:
    """Representa el dashboard de administrador."""

    # Selectores principales
    TAB_DASHBOARD = '[data-testid="tab-dashboard"], button:has-text("Dashboard")'
    TAB_REPORTS = '[data-testid="tab-reports"], button:has-text("Reports"), button:has-text("Reportes")'
    TAB_CONFIG = '[data-testid="tab-config"], button:has-text("Settings"), button:has-text("Configuración")'
    TAB_USERS = '[data-testid="tab-users"], button:has-text("Users"), button:has-text("Usuarios")'
    TAB_AUDIT = '[data-testid="tab-audit"], button:has-text("Audit"), button:has-text("Auditoría")'

    # Selectores para dashboard/métricas
    METRIC_TOTAL_TICKETS = '[data-testid="metric-total"], .metric-card:has-text("Total"), .card-total'
    METRIC_OPEN = '[data-testid="metric-open"], .metric-card:has-text("Open"), .card-open'
    METRIC_IN_PROGRESS = '[data-testid="metric-in-progress"], .metric-card:has-text("In Progress"), .card-in-progress'
    METRIC_RESOLVED = '[data-testid="metric-resolved"], .metric-card:has-text("Resolved"), .card-resolved'
    METRIC_SLA_COMPLIANCE = '[data-testid="metric-sla"], .metric-card:has-text("SLA"), .card-sla'
    METRIC_AVG_RESOLUTION_TIME = '[data-testid="metric-resolution-time"], .metric-card:has-text("Resolution"), .card-avg-time'

    # Selectores para valores en métricas
    METRIC_VALUE = '.metric-value, .card-value, .stat-number, h3'
    METRIC_LABEL = '.metric-label, .card-label, .stat-label, p'

    # Selectores para gráficos
    CHART_TICKETS_TREND = '[data-testid="chart-trend"], .chart-trend, canvas'
    CHART_PRIORITY_DISTRIBUTION = '[data-testid="chart-priority"], .chart-priority, svg'
    CHART_TECHNICIAN_LOAD = '[data-testid="chart-load"], .chart-technician-load'

    # Selectores para tabla de tickets (admin view)
    TABLE_TICKETS = '[data-testid="table-tickets"], table, .tickets-table'
    TICKET_ROW = '[data-testid="ticket-row"], tr:not(:first-child), .table-row'
    TICKET_ID = 'td:nth-child(1), [data-testid="col-id"]'
    TICKET_TITLE = 'td:nth-child(2), [data-testid="col-title"]'
    TICKET_STATUS = 'td:nth-child(3), [data-testid="col-status"]'
    TICKET_PRIORITY = 'td:nth-child(4), [data-testid="col-priority"]'
    TICKET_ASSIGNEE = 'td:nth-child(5), [data-testid="col-assignee"]'
    TICKET_CREATED = 'td:nth-child(6), [data-testid="col-created"]'

    # Selectores para reportes
    BUTTON_EXPORT_REPORT = '[data-testid="export-report"], button:has-text("Export"), button:has-text("Exportar")'
    SELECT_REPORT_FORMAT = '[data-testid="format-select"], select[name="format"], [role="combobox"]'
    SELECT_REPORT_TYPE = '[data-testid="report-type"], select[name="type"], [role="listbox"]'
    BUTTON_GENERATE_REPORT = '[data-testid="generate-report"], button:has-text("Generate"), button:has-text("Generar")'

    # Selectores para configuración
    SECTION_SLA_CONFIG = '[data-testid="section-sla"], .config-section:has-text("SLA")'
    SECTION_TEAMS_CONFIG = '[data-testid="section-teams"], .config-section:has-text("Teams")'
    SECTION_LDAP_CONFIG = '[data-testid="section-ldap"], .config-section:has-text("LDAP")'
    BUTTON_SAVE_CONFIG = '[data-testid="save-config"], button:has-text("Save"), button:has-text("Guardar")'

    # Selectores para usuarios
    TABLE_USERS = '[data-testid="table-users"], table, .users-table'
    USER_ROW = '[data-testid="user-row"], tr:not(:first-child), .user-row'
    BUTTON_ADD_USER = '[data-testid="add-user"], button:has-text("Add User"), button:has-text("Agregar Usuario")'
    BUTTON_EDIT_USER = '[data-testid="edit-user"], button:has-text("Edit")'
    BUTTON_DELETE_USER = '[data-testid="delete-user"], button:has-text("Delete"), button:has-text("Eliminar")'

    # Selectores para auditoría
    TABLE_AUDIT_LOG = '[data-testid="table-audit"], table, .audit-table'
    AUDIT_ROW = '[data-testid="audit-row"], tr:not(:first-child), .log-row'
    AUDIT_USER = 'td:nth-child(1), [data-testid="col-user"]'
    AUDIT_ACTION = 'td:nth-child(2), [data-testid="col-action"]'
    AUDIT_TIMESTAMP = 'td:nth-child(3), [data-testid="col-timestamp"]'
    AUDIT_IP = 'td:nth-child(4), [data-testid="col-ip"]'

    def __init__(self, page: Page):
        """Inicializa AdminDashboardPage con referencia a página."""
        self.page = page

    def is_on_admin_dashboard(self) -> bool:
        """
        Verifica si estamos en dashboard de admin.

        Returns:
            True si URL contiene /admin
        """
        return "/admin" in self.page.url

    def switch_to_dashboard(self) -> bool:
        """
        Cambia a pestaña Dashboard.

        Returns:
            True si cambio fue exitoso
        """
        try:
            self.page.click(self.TAB_DASHBOARD)
            self.page.wait_for_load_state("networkidle")
            return True
        except Exception:
            return False

    def switch_to_reports(self) -> bool:
        """
        Cambia a pestaña Reportes.

        Returns:
            True si cambio fue exitoso
        """
        try:
            self.page.click(self.TAB_REPORTS)
            self.page.wait_for_load_state("networkidle")
            return True
        except Exception:
            return False

    def get_metric_value(self, metric_selector: str) -> Optional[str]:
        """
        Obtiene el valor de una métrica.

        Args:
            metric_selector: Selector del elemento métrica

        Returns:
            Valor como string, o None si no encontrado
        """
        try:
            metric_elem = self.page.query_selector(metric_selector)
            if not metric_elem:
                return None

            # Intentar obtener valor directo o de subelemento
            value_elem = metric_elem.query_selector(self.METRIC_VALUE)
            if value_elem:
                return value_elem.text_content().strip()

            # Si no hay subelemento, obtener texto del elemento principal
            return metric_elem.text_content().strip()
        except Exception:
            return None

    def get_dashboard_metrics(self) -> Dict[str, Optional[str]]:
        """
        Obtiene todos los valores de métricas del dashboard.

        Returns:
            Dict con nombre métrica -> valor
        """
        metrics = {
            "total_tickets": self.get_metric_value(self.METRIC_TOTAL_TICKETS),
            "open": self.get_metric_value(self.METRIC_OPEN),
            "in_progress": self.get_metric_value(self.METRIC_IN_PROGRESS),
            "resolved": self.get_metric_value(self.METRIC_RESOLVED),
            "sla_compliance": self.get_metric_value(self.METRIC_SLA_COMPLIANCE),
            "avg_resolution_time": self.get_metric_value(self.METRIC_AVG_RESOLUTION_TIME),
        }
        return metrics

    def verify_metrics_visible(self) -> bool:
        """
        Verifica que métricas principales sean visibles.

        Returns:
            True si al menos 3 métricas están presentes
        """
        try:
            metrics_count = 0
            for selector in [
                self.METRIC_TOTAL_TICKETS,
                self.METRIC_OPEN,
                self.METRIC_RESOLVED,
                self.METRIC_SLA_COMPLIANCE
            ]:
                if self.page.query_selector(selector):
                    metrics_count += 1

            return metrics_count >= 3
        except Exception:
            return False

    def verify_charts_visible(self) -> bool:
        """
        Verifica que gráficos sean visibles.

        Returns:
            True si al menos 1 gráfico es visible
        """
        try:
            chart_count = 0
            for selector in [
                self.CHART_TICKETS_TREND,
                self.CHART_PRIORITY_DISTRIBUTION,
                self.CHART_TECHNICIAN_LOAD
            ]:
                if self.page.query_selector(selector):
                    chart_count += 1

            return chart_count >= 1
        except Exception:
            return False

    def export_report(self, report_format: str = "CSV") -> bool:
        """
        Exporta reporte en formato especificado.

        Args:
            report_format: Formato (CSV, PDF, Excel)

        Returns:
            True si exportación fue iniciada
        """
        try:
            # Seleccionar formato
            try:
                self.page.select_option(self.SELECT_REPORT_FORMAT, report_format)
                self.page.wait_for_timeout(300)
            except Exception:
                # Si no es select, buscar opción por texto
                self.page.click(f"text={report_format}")
                self.page.wait_for_timeout(300)

            # Click exportar
            self.page.click(self.BUTTON_EXPORT_REPORT)
            self.page.wait_for_load_state("networkidle")
            return True
        except Exception as e:
            print(f"Error exportando reporte: {e}")
            return False

    def get_ticket_count_from_table(self) -> int:
        """
        Obtiene cantidad de tickets en tabla visible.

        Returns:
            Número de filas de ticket
        """
        try:
            rows = self.page.query_selector_all(self.TICKET_ROW)
            return len(rows)
        except Exception:
            return 0

    def get_audit_log_count(self) -> int:
        """
        Obtiene cantidad de entradas en log de auditoría.

        Returns:
            Número de entradas
        """
        try:
            self.page.click(self.TAB_AUDIT)
            self.page.wait_for_load_state("networkidle")
            rows = self.page.query_selector_all(self.AUDIT_ROW)
            return len(rows)
        except Exception:
            return 0

    def verify_audit_log_visible(self) -> bool:
        """
        Verifica que tabla de auditoría sea visible.

        Returns:
            True si tabla existe
        """
        try:
            self.page.click(self.TAB_AUDIT)
            self.page.wait_for_load_state("networkidle")
            table = self.page.query_selector(self.TABLE_AUDIT_LOG)
            return table is not None
        except Exception:
            return False

    def get_audit_entries(self, limit: int = 10) -> List[Dict]:
        """
        Obtiene últimas entradas del log de auditoría.

        Args:
            limit: Máximo número de entradas a retornar

        Returns:
            Lista de dicts con datos de auditoría
        """
        try:
            self.page.click(self.TAB_AUDIT)
            self.page.wait_for_load_state("networkidle")

            entries = []
            rows = self.page.query_selector_all(self.AUDIT_ROW)

            for row in rows[:limit]:
                user_elem = row.query_selector(self.AUDIT_USER)
                action_elem = row.query_selector(self.AUDIT_ACTION)
                timestamp_elem = row.query_selector(self.AUDIT_TIMESTAMP)
                ip_elem = row.query_selector(self.AUDIT_IP)

                entries.append({
                    "user": user_elem.text_content().strip() if user_elem else None,
                    "action": action_elem.text_content().strip() if action_elem else None,
                    "timestamp": timestamp_elem.text_content().strip() if timestamp_elem else None,
                    "ip": ip_elem.text_content().strip() if ip_elem else None,
                })

            return entries
        except Exception as e:
            print(f"Error obteniendo entradas auditoría: {e}")
            return []

    def get_user_count(self) -> int:
        """
        Obtiene cantidad de usuarios registrados.

        Returns:
            Número de usuarios
        """
        try:
            self.page.click(self.TAB_USERS)
            self.page.wait_for_load_state("networkidle")
            rows = self.page.query_selector_all(self.USER_ROW)
            return len(rows)
        except Exception:
            return 0

    def save_config(self) -> bool:
        """
        Guarda configuración actual.

        Returns:
            True si guardado fue exitoso
        """
        try:
            self.page.click(self.BUTTON_SAVE_CONFIG)
            self.page.wait_for_load_state("networkidle")
            return True
        except Exception:
            return False
