# Guía Rápida de Refactoring - TicketDesk Enterprise

**Objetivo:** Convertir monolito (1,632 líneas) a Clean Architecture estructurada  
**Duración:** 8 semanas  
**Equipos:** 2-3 desarrolladores  

---

## Checklist de Implementación por Fase

### ✓ PHASE 1: Setup Inicial (Week 1, ~4 horas)

**Crear estructura base sin romper funcionalidad**

```bash
# Crear directorios
mkdir -p ticketdesk/{domain,application,infrastructure,presentation,tests}
mkdir -p ticketdesk/application/{services,ports}
mkdir -p ticketdesk/infrastructure/{database/{repositories,migrations},auth,email,webhooks,cache,monitoring}
mkdir -p ticketdesk/presentation/{blueprints,middlewares,websocket,serializers}
mkdir -p ticketdesk/tests/{unit,integration,e2e}
mkdir -p docs/decisions

# Crear archivos stub vacíos
touch ticketdesk/{domain,application,infrastructure,presentation}/__init__.py
touch ticketdesk/config.py
touch ticketdesk/main.py
```

**Archivos a crear (vacíos de momento):**

| Archivo | Propósito |
|---------|-----------|
| `ticketdesk/config.py` | Configuración por entorno (dev, test, prod) |
| `ticketdesk/domain/__init__.py` | Entities, enums, value objects |
| `ticketdesk/application/__init__.py` | DTOs, services, ports |
| `ticketdesk/infrastructure/__init__.py` | BD, auth, email, webhooks |
| `ticketdesk/presentation/__init__.py` | Blueprints, middlewares, WebSocket |
| `ticketdesk/main.py` | Entry point (reemplaza app.py) |
| `tests/conftest.py` | Fixtures para pytest |

**Tests:**
- [ ] Estructura creada
- [ ] `python -c "import ticketdesk"` funciona sin errores

---

### ✓ PHASE 2: Domain Layer (Weeks 2-3, ~40 horas)

**Extraer modelos de negocio sin dependencias externas**

#### 2.1 Crear `ticketdesk/domain/entities.py`

Convertir modelos SQLAlchemy a dataclasses puro:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum

class TicketStatus(Enum):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    CLOSED = 'closed'

class Priority(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

@dataclass
class Ticket:
    id: Optional[int]
    ticket_number: str
    title: str
    description: str
    status: TicketStatus
    priority: Priority
    company_id: int
    creator_id: int
    assignee_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    version: int
    sla_deadline: Optional[datetime]
    sla_minutes: Optional[int]
    
    @property
    def sla_remaining_minutes(self) -> Optional[int]:
        """Calcula minutos restantes de SLA"""
        if not self.sla_deadline:
            return None
        remaining = self.sla_deadline - datetime.now()
        return max(0, int(remaining.total_seconds() / 60))

@dataclass
class User:
    id: int
    username: str
    name: str
    email: str
    role: str
    company_id: int
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
```

**Otras entities:**
- [ ] Company
- [ ] Message
- [ ] Template
- [ ] Server
- [ ] Config (settings)
- [ ] AuditLog
- [ ] BotKnowledge
- [ ] Webhook

#### 2.2 Crear `ticketdesk/domain/enums.py`

```python
from enum import Enum

class UserRole(Enum):
    ADMIN = 'admin'
    TECHNICIAN = 'technician'
    EMPLOYEE = 'employee'

class TicketStatus(Enum):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'

# ... más enums
```

#### 2.3 Crear `ticketdesk/domain/exceptions.py`

```python
class DomainException(Exception):
    """Base para excepciones de dominio"""
    pass

class TicketNotFoundError(DomainException):
    pass

class ValidationError(DomainException):
    pass

class UnauthorizedError(DomainException):
    pass

class CompanyMismatchError(DomainException):
    """Intentó acceder a recurso de otra empresa"""
    pass
```

#### 2.4 Crear `ticketdesk/domain/value_objects.py`

```python
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class Email:
    """Objeto de valor para email"""
    address: str
    
    def __post_init__(self):
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', self.address):
            raise ValueError(f"Invalid email: {self.address}")

@dataclass(frozen=True)
class TicketNumber:
    """Objeto de valor para número de ticket"""
    company: str
    sequence: int
    
    def __str__(self) -> str:
        return f"TKT-{self.company.upper()}-{self.sequence:05d}"
```

**Tests:**
- [ ] 10+ entities modeladas
- [ ] 0 dependencias externas (sin imports de Flask, SQLAlchemy)
- [ ] Type hints 100%
- [ ] `pytest tests/unit/test_entities.py` pasa

---

### ✓ PHASE 2B: Persistence Layer (Weeks 2-3, ~40 horas)

**Crear abstracciones (ports) y implementaciones (repositories)**

#### 2B.1 Crear `ticketdesk/application/ports/ticket_repository.py`

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from ticketdesk.domain.entities import Ticket

class TicketRepository(ABC):
    """Interfaz para persistencia de Ticket"""
    
    @abstractmethod
    def create(self, ticket: Ticket) -> int:
        """Crea ticket, retorna ID"""
        pass
    
    @abstractmethod
    def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        """Obtiene por ID"""
        pass
    
    @abstractmethod
    def list_by_company(self, company_id: int, 
                       limit: int = 100) -> List[Ticket]:
        """Lista tickets de empresa"""
        pass
    
    @abstractmethod
    def search(self, company_id: int, query: str) -> List[Ticket]:
        """Búsqueda de texto completo"""
        pass
    
    @abstractmethod
    def update(self, ticket: Ticket) -> bool:
        """Actualiza (versioning optimista)"""
        pass
    
    @abstractmethod
    def delete(self, ticket_id: int) -> bool:
        """Elimina"""
        pass
```

**Otros ports a crear:**
- [ ] `application/ports/user_repository.py`
- [ ] `application/ports/company_repository.py`
- [ ] `application/ports/audit_repository.py`
- [ ] `application/ports/email_gateway.py`
- [ ] `application/ports/auth_provider.py`
- [ ] `application/ports/webhook_gateway.py`

#### 2B.2 Crear `ticketdesk/infrastructure/database/models.py`

Mantener SQLAlchemy models SOLO para BD:

```python
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from ticketdesk.domain.entities import Ticket

db = SQLAlchemy()

class TicketModel(db.Model):
    """SQLAlchemy model para persistencia"""
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    # ... todas las columnas
    
    # Mapper a entidad de dominio
    def to_domain(self) -> Ticket:
        return Ticket(
            id=self.id,
            ticket_number=self.ticket_number,
            title=self.title,
            # ...
        )
    
    @staticmethod
    def from_domain(ticket: Ticket) -> 'TicketModel':
        return TicketModel(
            ticket_number=ticket.ticket_number,
            title=ticket.title,
            # ...
        )
```

#### 2B.3 Crear `ticketdesk/infrastructure/database/repositories/ticket_repository.py`

```python
from ticketdesk.application.ports.ticket_repository import TicketRepository
from ticketdesk.infrastructure.database.models import TicketModel, db
from ticketdesk.domain.entities import Ticket

class SQLiteTicketRepository(TicketRepository):
    """Implementación SQLite"""
    
    def create(self, ticket: Ticket) -> int:
        model = TicketModel.from_domain(ticket)
        db.session.add(model)
        db.session.commit()
        return model.id
    
    def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        model = TicketModel.query.get(ticket_id)
        return model.to_domain() if model else None
    
    def update(self, ticket: Ticket) -> bool:
        """Update con versioning optimista"""
        model = TicketModel.query.get(ticket.id)
        if not model:
            return False
        
        # Verificar versión (optimistic locking)
        if model.version != ticket.version:
            return False  # Conflict
        
        # Actualizar
        model = TicketModel.from_domain(ticket)
        model.version += 1
        db.session.merge(model)
        db.session.commit()
        return True
    
    # ... más métodos
```

**Tests:**
- [ ] 6 repositories implementados
- [ ] `pytest tests/integration/test_ticket_repository.py` pasa
- [ ] In-memory repository existe para tests unitarios

---

### ✓ PHASE 3: Application Layer - Services (Weeks 3-4, ~60 horas)

**Lógica de negocio en servicios, sin Flask/BD**

#### 3.1 Crear `ticketdesk/application/services/ticket_service.py`

```python
from typing import List, Optional
from ticketdesk.application.ports.ticket_repository import TicketRepository
from ticketdesk.application.ports.audit_repository import AuditRepository
from ticketdesk.domain.entities import Ticket, TicketStatus
from ticketdesk.domain.exceptions import (
    TicketNotFoundError, ValidationError, UnauthorizedError
)

class TicketService:
    """Casos de uso para tickets"""
    
    def __init__(self, 
                 ticket_repo: TicketRepository,
                 audit_repo: AuditRepository,
                 sla_service: 'SLAService'):
        self.ticket_repo = ticket_repo
        self.audit_repo = audit_repo
        self.sla_service = sla_service
    
    def create_ticket(self, 
                     title: str, 
                     description: str,
                     priority: str,
                     creator_id: int,
                     company_id: int) -> Ticket:
        """Crear nuevo ticket (RF-01-02)"""
        
        # Validar input
        if not title or len(title) > 200:
            raise ValidationError("Title required, max 200 chars")
        
        if len(description) < 10:
            raise ValidationError("Description too short")
        
        # Crear entidad
        ticket = Ticket(
            id=None,
            ticket_number=self.ticket_repo.next_number(company_id),
            title=title,
            description=description,
            status=TicketStatus.OPEN,
            priority=priority,
            company_id=company_id,
            creator_id=creator_id,
            assignee_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            resolved_at=None,
            version=1,
            sla_deadline=self.sla_service.calculate_deadline(
                priority, company_id
            ),
            sla_minutes=None,
        )
        
        # Persistir
        ticket_id = self.ticket_repo.create(ticket)
        ticket.id = ticket_id
        
        # Auditar
        self.audit_repo.log(
            action='ticket_created',
            user_id=creator_id,
            entity_type='ticket',
            entity_id=ticket_id,
            company_id=company_id,
            description=f"Ticket {ticket.ticket_number} creado"
        )
        
        return ticket
    
    def resolve_ticket(self,
                      ticket_id: int,
                      resolver_id: int,
                      company_id: int) -> Ticket:
        """Resolver ticket (RF-01-05)"""
        
        ticket = self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found")
        
        # Validar segregación de empresa
        if ticket.company_id != company_id:
            raise UnauthorizedError("Company mismatch")
        
        if ticket.status == TicketStatus.RESOLVED:
            raise ValidationError("Ticket already resolved")
        
        # Cambiar estado
        ticket.status = TicketStatus.RESOLVED
        ticket.resolved_at = datetime.now()
        ticket.version += 1
        
        # Persistir con optimistic locking
        if not self.ticket_repo.update(ticket):
            raise ValidationError("Conflict: ticket modified, retry")
        
        # Auditar
        self.audit_repo.log(
            action='ticket_resolved',
            user_id=resolver_id,
            entity_type='ticket',
            entity_id=ticket_id,
            company_id=company_id,
            description=f"Ticket {ticket.ticket_number} resuelto"
        )
        
        return ticket
    
    def search(self, company_id: int, query: str) -> List[Ticket]:
        """Búsqueda (RF-01-10)"""
        if len(query) < 3:
            raise ValidationError("Search query too short")
        
        return self.ticket_repo.search(company_id, query)
    
    # ... más casos de uso
```

**Otros servicios:**
- [ ] `UserService` (autenticación, CRUD usuarios)
- [ ] `CompanyService` (CRUD empresas, segregación)
- [ ] `SLAService` (cálculo de deadlines)
- [ ] `AssignmentService` (asignación automática con IA)
- [ ] `AuditService` (logging)
- [ ] `NotificationService` (email, webhooks)

**Tests:**
- [ ] 40+ tests unitarios (`tests/unit/test_ticket_service.py`, etc.)
- [ ] 0 dependencias de Flask, BD, Socket.IO
- [ ] Cobertura >80%

```bash
pytest tests/unit/ --cov=ticketdesk/application/services
```

---

### ✓ PHASE 4: Presentation Layer - Blueprints (Week 4+, ~80 horas)

**Convertir rutas de app.py a blueprints, usar servicios**

#### 4.1 Crear `ticketdesk/presentation/app.py`

```python
from flask import Flask
from flask_socketio import SocketIO
from ticketdesk.infrastructure.database.models import db
from ticketdesk.config import Config

def create_app(config_class=None):
    """Flask app factory"""
    
    app = Flask(__name__)
    app.config.from_object(config_class or Config)
    
    # Inicializar extensiones
    db.init_app(app)
    socketio_instance = SocketIO(app, cors_allowed_origins="*")
    
    with app.app_context():
        # Crear tablas
        db.create_all()
        
        # Inyectar dependencias
        from ticketdesk.infrastructure.database.repositories import *
        from ticketdesk.application.services import *
        
        app.ticket_service = TicketService(
            ticket_repo=SQLiteTicketRepository(),
            audit_repo=SQLiteAuditRepository(),
            sla_service=SLAService()
        )
        app.user_service = UserService(user_repo, auth_provider)
        app.company_service = CompanyService(company_repo)
        # ... más servicios
        
        # Registrar blueprints
        from ticketdesk.presentation.blueprints import (
            auth_bp, employee_bp, technician_bp, admin_bp, api_bp, health_bp
        )
        
        app.register_blueprint(auth_bp)
        app.register_blueprint(employee_bp, url_prefix='/employee')
        app.register_blueprint(technician_bp, url_prefix='/technician')
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(api_bp, url_prefix='/api')
        app.register_blueprint(health_bp, url_prefix='/api')
        
        # Registrar middlewares
        from ticketdesk.presentation.middlewares import *
        # ...
    
    return app, socketio_instance
```

#### 4.2 Crear blueprints

**`ticketdesk/presentation/blueprints/auth_bp.py`:**

```python
from flask import Blueprint, request, session, jsonify, redirect
from functools import wraps
from ticketdesk.application.dto import AuthDTO
from ticketdesk.domain.exceptions import ValidationError, UnauthorizedError

auth_bp = Blueprint('auth', __name__)

def require_auth(f):
    """Decorator: usuario autenticado"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

def require_role(*roles):
    """Decorator: verificar role"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                return jsonify({'success': False, 'error': 'Forbidden'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

@auth_bp.route('/login', methods=['POST'])
def login():
    """Autenticación"""
    user_service = current_app.user_service
    
    try:
        user, token = user_service.authenticate(
            username=request.json['username'],
            password=request.json['password'],
            company_code=request.json['company']
        )
        
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session['company_id'] = user.company_id
        
        return jsonify({
            'success': True,
            'token': token,
            'user': UserSerializer().dump(user)
        })
    
    except UnauthorizedError as e:
        return jsonify({'success': False, 'error': str(e)}), 401
```

**`ticketdesk/presentation/blueprints/employee_bp.py`:**

```python
from flask import Blueprint, render_template, request, jsonify, session, current_app
from ticketdesk.presentation.blueprints.auth_bp import require_auth
from ticketdesk.application.exceptions import ValidationError

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/dashboard')
@require_auth
def dashboard():
    """Dashboard de empleado"""
    ticket_service = current_app.ticket_service
    
    tickets = ticket_service.list_my_created_tickets(
        user_id=session['user_id'],
        company_id=session['company_id']
    )
    
    return render_template('employee/dashboard.html',
                         tickets=[TicketSerializer().dump(t) for t in tickets])

@employee_bp.route('/create', methods=['POST'])
@require_auth
def create_ticket():
    """Crear ticket"""
    ticket_service = current_app.ticket_service
    
    try:
        ticket = ticket_service.create_ticket(
            title=request.json['title'],
            description=request.json['description'],
            priority=request.json.get('priority', 'medium'),
            creator_id=session['user_id'],
            company_id=session['company_id']
        )
        
        # Emitir evento WebSocket
        socketio.emit('ticket_created',
                     TicketSerializer().dump(ticket),
                     room=f"company_{session['company_id']}")
        
        return jsonify({
            'success': True,
            'ticket': TicketSerializer().dump(ticket)
        }), 201
    
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 422
```

**Crear similares:**
- [ ] `admin_bp.py` (config, empresas, usuarios)
- [ ] `technician_bp.py` (cola, asignación)
- [ ] `api_bp.py` (búsqueda, exportar, SLA)
- [ ] `health_bp.py` (health check, métricas)

**Criterios:**
- [ ] Cada ruta <30 líneas
- [ ] Sin lógica de negocio (solo orchestración)
- [ ] Input validation → DTO
- [ ] Service call
- [ ] Serializar output
- [ ] Error handling

**Tests:**
- [ ] `tests/integration/test_employee_routes.py` (mocking service)
- [ ] `tests/e2e/test_create_ticket_flow.py` (full stack)

---

### ✓ PHASE 5: Infrastructure - Auth, Email, Webhooks (Week 5, ~40 horas)

**Abstraer y centralizar integraciones**

#### 5.1 Auth `ticketdesk/infrastructure/auth/jwt_provider.py`

```python
from ticketdesk.application.ports.auth_provider import AuthProvider
import jwt
import uuid

class JWTProvider(AuthProvider):
    """Implementación JWT"""
    
    def __init__(self, secret_key: str, blacklist_repo):
        self.secret_key = secret_key
        self.blacklist_repo = blacklist_repo
    
    def generate_token(self, user_id: int, company_id: int) -> str:
        jti = str(uuid.uuid4())
        payload = {
            'user_id': user_id,
            'company_id': company_id,
            'jti': jti,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=8)
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256'), jti
    
    def verify_token(self, token: str) -> Dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Verificar blacklist (<5ms)
            if self.blacklist_repo.is_blacklisted(payload['jti']):
                return None
            
            return payload
        except:
            return None
    
    def revoke_token(self, jti: str):
        """Invalidar token (logout)"""
        self.blacklist_repo.add(jti, exp_time)
```

#### 5.2 Email `ticketdesk/infrastructure/email/smtp_gateway.py`

```python
from ticketdesk.application.ports.email_gateway import EmailGateway
import smtplib
from email.mime.text import MIMEText

class SMTPEmailGateway(EmailGateway):
    """Implementación SMTP"""
    
    def send_email(self, to: str, subject: str, body: str,
                  html: Optional[str] = None) -> bool:
        try:
            msg = MIMEText(html or body, 'html' if html else 'plain')
            msg['Subject'] = subject
            msg['From'] = self.from_address
            msg['To'] = to
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            self.logger.error(f"Email failed: {e}")
            # Implementar retry con backoff exponencial
            return False
```

#### 5.3 Webhooks `ticketdesk/infrastructure/webhooks/teams_gateway.py`

```python
from ticketdesk.application.ports.webhook_gateway import WebhookGateway
import requests

class TeamsWebhookGateway(WebhookGateway):
    """Notificaciones a Microsoft Teams"""
    
    def __init__(self, webhook_repo):
        self.webhook_repo = webhook_repo
    
    def notify(self, event: str, ticket: Ticket) -> bool:
        webhooks = self.webhook_repo.find_by_event(event, ticket.company_id)
        
        for webhook in webhooks:
            try:
                message = self._format_message(event, ticket)
                requests.post(webhook.url, json=message, timeout=5)
            except Exception as e:
                logger.error(f"Webhook failed: {e}")
        
        return True
    
    def _format_message(self, event: str, ticket: Ticket) -> Dict:
        # Format Teams message card
        return {
            '@type': 'MessageCard',
            '@context': 'https://schema.org/extensions',
            'summary': f'Ticket {event}',
            'themeColor': self._get_color(ticket.priority),
            'sections': [{
                'activityTitle': f'{ticket.ticket_number}: {ticket.title}',
                'facts': [
                    {'name': 'Status', 'value': ticket.status},
                    {'name': 'Priority', 'value': ticket.priority},
                ]
            }]
        }
```

**Más infraestructura:**
- [ ] `LDAP Provider` (autenticación por empresa)
- [ ] `Password hasher` (PBKDF2 con salt)
- [ ] `Cache provider` (Redis blacklist)
- [ ] `Slack gateway` (webhooks alternativa)

**Tests:**
- [ ] `tests/integration/test_jwt_provider.py`
- [ ] `tests/integration/test_email_gateway.py`
- [ ] Verify <5ms JWT blacklist lookup

---

### ✓ PHASE 6: WebSocket Refactor (Week 6, ~20 horas)

**Salas por empresa, heartbeat, reconexión**

#### 6.1 `ticketdesk/presentation/websocket/handlers.py`

```python
from flask_socketio import socketio, emit, join_room, leave_room

@socketio.on('connect')
def handle_connect():
    """Usuario conectado"""
    if 'user_id' not in session:
        return False
    
    user_id = session['user_id']
    company_id = session['company_id']
    
    # Unirse a sala de empresa
    room = f"company_{company_id}"
    join_room(room)
    
    # Registrar sesión
    session_service = current_app.session_service
    session_service.register_ws_session(user_id, request.sid)
    
    emit('connected', {
        'message': 'Conectado',
        'user_id': user_id,
        'room': room
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Usuario desconectado"""
    user_id = session.get('user_id')
    session_service = current_app.session_service
    session_service.unregister_ws_session(user_id)

@socketio.on('ping')
def handle_ping():
    """Heartbeat"""
    emit('pong')

# Emisores (llamados desde servicios)
def emit_ticket_created(ticket: Ticket):
    socketio.emit('ticket_created',
                 TicketSerializer().dump(ticket),
                 room=f"company_{ticket.company_id}")

def emit_ticket_updated(ticket: Ticket):
    socketio.emit('ticket_updated',
                 TicketSerializer().dump(ticket),
                 room=f"company_{ticket.company_id}")
```

**Tests:**
- [ ] `tests/integration/test_websocket.py`
- [ ] Verificar segregación de empresa
- [ ] Heartbeat timeout después de 15 min

---

### ✓ PHASE 7: Testing & Documentation (Weeks 7-8, ~60 horas)

#### 7.1 Test Coverage

```bash
# Crear tests
pytest tests/unit/ --cov=ticketdesk
# Esperar >80% cobertura en application, infrastructure
```

**Coverage goals:**
- [ ] domain/: 100% (crítico)
- [ ] application/services/: >90%
- [ ] application/ports/: N/A (interfaces)
- [ ] infrastructure/: >80%
- [ ] presentation/blueprints/: >70% (difícil testear rutas)

#### 7.2 Documentación

- [ ] `docs/ARCHITECTURE.md` (visión general)
- [ ] `docs/API.md` (endpoints)
- [ ] `docs/TESTING.md` (cómo escribir tests)
- [ ] `docs/DEPLOYMENT.md` (cómo desplegar)
- [ ] ADRs en `docs/decisions/`

#### 7.3 Performance Benchmarking

```python
# tests/benchmark/test_search.py
@pytest.mark.benchmark
def test_search_1m_tickets(benchmark):
    service = create_ticket_service()
    result = benchmark(service.search, company_id=1, query='test')
    # Esperar: <200ms
```

---

## Checklist de Aceptación

- [ ] Estructura creada (Phase 1)
- [ ] Domain + entities (Phase 2)
- [ ] Repositories + ports (Phase 2B)
- [ ] Services implementados (Phase 3)
- [ ] Blueprints creados (Phase 4)
- [ ] Infrastructure abstraída (Phase 5)
- [ ] WebSocket refactorizado (Phase 6)
- [ ] Tests >80% coverage (Phase 7)
- [ ] Documentación completa (Phase 7)
- [ ] Zero regressions en tests E2E
- [ ] API response times ≤500ms
- [ ] JWT blacklist lookup <5ms
- [ ] Company segregation en toda la BD

---

## Timesheet Estimado

| Phase | Duración | Esfuerzo | Personas |
|-------|----------|----------|----------|
| 1: Setup | 4h | Bajo | 1 |
| 2: Domain | 40h | Medio | 2 |
| 2B: Repositories | 40h | Medio | 2 |
| 3: Services | 60h | Alto | 2-3 |
| 4: Blueprints | 80h | Alto | 3 |
| 5: Infrastructure | 40h | Medio | 2 |
| 6: WebSocket | 20h | Bajo | 1 |
| 7: Testing | 40h | Medio | 2 |
| 7: Documentation | 20h | Bajo | 1 |
| **TOTAL** | **340 horas** | **~8 semanas** | **2-3 personas** |

---

## Riesgos y Mitigación

| Riesgo | Mitigación |
|--------|-----------|
| Regresiones | Tests E2E antes de cada phase, staging env |
| Specs incompletas | Review CLAUDE.md, RF* requirements |
| Performance loss | Benchmarking continuo, profiling |
| Team adoption | Documentation + pair programming |
| DB migrations | Alembic setup temprano |

---

## Comandos Útiles

```bash
# Crear estructura
python scripts/init_refactoring.py

# Tests
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/e2e/ -v
pytest --cov=ticketdesk

# Type checking
mypy ticketdesk/

# Lint
flake8 ticketdesk/ --max-line-length=120

# Format
black ticketdesk/ tests/

# Run app
python main.py
```

---

## Preguntas Frecuentes

**P: ¿Y si encuentro un bug durante refactoring?**  
R: Documentalo en issue, priority baja. Continúa refactoring en rama feature.

**P: ¿Puedo usar FastAPI instead?**  
R: No. FastAPI requiere rewrite total. Clean Architecture es más bajo riesgo.

**P: ¿Y si necesito agregar feature urgentemente?**  
R: Pausar refactoring, implementar en rama emergencia, mergear después.

**P: ¿Type hints son obligatorios?**  
R: Sí. 100% type hints hace el código autodocumentado.

**P: ¿Qué pasa con app.py?**  
R: No eliminarla. Mantener como `main_old.py` para referencia histórica.
