"""
Page Object Models para TicketDesk Enterprise E2E tests.

Este módulo contiene clases que representan páginas/pantallas de la aplicación,
encapsulando selectores y métodos de interacción.
"""

from .LoginPage import LoginPage
from .EmployeeDashboardPage import EmployeeDashboardPage
from .TechnicianDashboardPage import TechnicianDashboardPage
from .AdminDashboardPage import AdminDashboardPage

__all__ = [
    "LoginPage",
    "EmployeeDashboardPage",
    "TechnicianDashboardPage",
    "AdminDashboardPage",
]
