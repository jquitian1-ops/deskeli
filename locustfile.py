"""
Locust: prueba de carga para DeskEli / TicketDesk Enterprise.

Uso rápido:
    pip install locust
    locust -f locustfile.py --host=http://localhost:5050
    # → abrir http://localhost:8089 y setear 4000 users con spawn-rate 100/s

Modo headless (para CI o comando único):
    locust -f locustfile.py --host=http://localhost:5050 \\
        --users 4000 --spawn-rate 100 --run-time 5m --headless \\
        --csv=reports/load_test

Env vars:
    LOAD_TEST_EMAIL_DOMAIN  → dominio para generar emails de test (default: patprimo.com.co)
    LOAD_TEST_PASSWORD      → password que TODOS los users de test comparten (default: Test1234!)
    LOAD_TEST_COMPANY       → empresa para el login (eliot|pash|primatela, default: pash)

Para que funcione tenés que tener creados en la BD users como
    empleado0001@dominio  ...  empleado4000@dominio
    con el mismo password. Ver scripts/seed_load_test_users.py (opcional).
"""
import os
import random
import time
from locust import HttpUser, task, between, events


LOAD_TEST_EMAIL_DOMAIN = os.getenv('LOAD_TEST_EMAIL_DOMAIN', 'patprimo.com.co')
LOAD_TEST_PASSWORD = os.getenv('LOAD_TEST_PASSWORD', 'Test1234!')
LOAD_TEST_COMPANY = os.getenv('LOAD_TEST_COMPANY', 'pash')

_user_counter = 0


def _next_email():
    """Cada instancia de Locust user pide un email único. Rota entre 4000 slots."""
    global _user_counter
    _user_counter = (_user_counter + 1) % 4000
    return f'empleado{_user_counter:04d}@{LOAD_TEST_EMAIL_DOMAIN}'


class EmpleadoDeskEli(HttpUser):
    """Simula un empleado navegando el portal: login → ver tickets → crear ticket
    ocasional → keep-alive de sesión."""

    wait_time = between(2, 8)   # 2-8 s entre acciones (usuario real)

    def on_start(self):
        """Ejecuta 1 sola vez al arrancar cada usuario simulado."""
        self.email = _next_email()
        self.logged_in = False
        self._login()

    def on_stop(self):
        if self.logged_in:
            self.client.post('/api/logout', name='POST /api/logout')

    def _login(self):
        payload = {
            'email': self.email,
            'password': LOAD_TEST_PASSWORD,
            'company': LOAD_TEST_COMPANY,
        }
        with self.client.post('/api/login', json=payload, catch_response=True, name='POST /api/login') as r:
            if r.status_code == 200 and r.json().get('success'):
                self.logged_in = True
                r.success()
            else:
                # Marcamos como fallo pero seguimos — así medimos si el login mismo satura
                r.failure(f'Login failed: {r.status_code} — {r.text[:200]}')

    # ── Golden path: navegación típica ────────────────────────────
    @task(6)
    def ver_mis_tickets(self):
        if not self.logged_in:
            return
        self.client.get('/api/tickets?scope=mine&limit=20', name='GET /api/tickets (mine)')

    @task(3)
    def ver_kb(self):
        if not self.logged_in:
            return
        self.client.get('/api/kb/search?q=contraseña', name='GET /api/kb/search')

    @task(2)
    def ping_session(self):
        if not self.logged_in:
            return
        self.client.get('/api/session/ping', name='GET /api/session/ping')

    @task(1)
    def health(self):
        # No requiere auth, endpoint más barato — hit continuo simula el
        # tráfico del status check del navegador y del monitor externo.
        self.client.get('/api/health', name='GET /api/health')

    @task(1)
    def crear_ticket(self):
        """Crear ticket = escritura a BD, el escenario más pesado."""
        if not self.logged_in:
            return
        payload = {
            'title': f'Load test ticket {random.randint(1, 100000)}',
            'description': 'Ticket generado automáticamente por Locust',
            'category': random.choice(['General', 'SAP', 'Servidores', 'Redes', 'Correo']),
            'priority': random.choice(['low', 'medium', 'high']),
        }
        with self.client.post('/api/tickets', json=payload, catch_response=True, name='POST /api/tickets') as r:
            if r.status_code in (200, 201):
                r.success()
            else:
                r.failure(f'{r.status_code} — {r.text[:200]}')


@events.test_start.add_listener
def _on_test_start(environment, **kwargs):
    print(f'''
    ═══════════════════════════════════════════════════════════
    DeskEli Load Test starting
    ═══════════════════════════════════════════════════════════
    Host:      {environment.host}
    Domain:    {LOAD_TEST_EMAIL_DOMAIN}
    Company:   {LOAD_TEST_COMPANY}
    Objetivo:  4000 users concurrentes / spawn-rate ≥100/s
    ═══════════════════════════════════════════════════════════
    ''')


@events.test_stop.add_listener
def _on_test_stop(environment, **kwargs):
    stats = environment.stats.total
    print(f'''
    ═══════════════════════════════════════════════════════════
    DeskEli Load Test finished
    ═══════════════════════════════════════════════════════════
    Total requests:   {stats.num_requests}
    Failures:         {stats.num_failures} ({stats.fail_ratio * 100:.2f}%)
    Avg response:     {stats.avg_response_time:.0f} ms
    p50 response:     {stats.get_response_time_percentile(0.50):.0f} ms
    p95 response:     {stats.get_response_time_percentile(0.95):.0f} ms
    p99 response:     {stats.get_response_time_percentile(0.99):.0f} ms
    Max response:     {stats.max_response_time:.0f} ms
    RPS:              {stats.total_rps:.1f}
    ═══════════════════════════════════════════════════════════
    Target CLAUDE.md: p95 ≤ 500 ms, failures = 0
    ═══════════════════════════════════════════════════════════
    ''')
