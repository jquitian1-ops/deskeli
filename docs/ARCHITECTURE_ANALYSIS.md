# Análisis Arquitectónico - TicketDesk Enterprise v2.1

**Fecha:** 2026-05-29  
**Estado:** Diagnóstico Completado  
**Versión Actual:** app.py con 1,632 líneas  
**Recomendación:** Refactoring a Blueprint + Capas (Prioridad Alta)

---

## Resumen Ejecutivo

**Problema Principal:** El archivo `app.py` contiene 1,632 líneas de código monolítico que mezcla:
- 10 modelos SQLAlchemy (Companies, Users, Tickets, Messages, etc.)
- 40+ rutas HTTP (mezcla de admin, employee, technician, API)
- Lógica de negocio dispersa (SLA, asignación automática, monitoring, webhooks)
- Utilidades y funciones de soporte (rate limiting, auditoría, email, backup)
- Configuración global y constantes

**Impacto:**
- Código duplicado (23 instancias de validación de admin, 41 operaciones DB sin abstracción)
- Bajo mantenibilidad: agregar feature requiere navegar 1,632 líneas
- Difícil testing: acoplamiento fuerte entre capas
- Escalabilidad limitada: agregar nuevas rutas es tedioso
- Riesgo de bugs: lógica dispersa en múltiples endpoints

**Recomendación:** Refactoring a **Architecture Blueprints + Servicios + Modelos** (4 semanas, 8-12 sprints)

---

## 1. Análisis Actual: Problemas Detectados

### 1.1 Monolito sin Separación de Capas

```
┌─────────────────────────────────────────┐
│         app.py (1,632 líneas)           │
│  ✗ Rutas HTTP                           │
│  ✗ Modelos SQLAlchemy                   │
│  ✗ Lógica de Negocio                    │
│  ✗ Middlewares                          │
│  ✗ Utilidades                           │
│  ✗ Configuración                        │
│  ✗ WebSocket                            │
│  ✗ Backup/Monitoring/Watchdog           │
└─────────────────────────────────────────┘
```

**Análisis Cuantitativo:**

| Aspecto | Cantidad | Problema |
|---------|----------|----------|
| Modelos | 10 | Distribuidos en líneas 107–250 |
| Rutas HTTP | 40+ | Mezcladas sin agrupación |
| Decoradores auth | 23 | Duplicación `if 'user_id' not in session` |
| db.session calls | 41 | Sin abstracción de repositorio |
| Funciones utilidad | 12+ | Ubicadas al azar |
| Threads + daemons | 4 | Watchdog, backup, monitoring, server ping |

### 1.2 Código Duplicado (Alto Riesgo)

#### Validación de Roles (23 repeticiones)

```python
# ❌ Patrón duplicado en todos los endpoints admin
if 'user_id' not in session or session['role'] != 'admin':
    return jsonify({'success': False}), 401
```

**Impacto:** Si cambias lógica de autorización, 23 lugares para actualizar.

#### Operaciones DB sin Abstracción (41 repeticiones)

```python
# ❌ db.session.add / db.session.commit duplicados
db.session.add(ticket)
db.session.commit()
```

**Impacto:** No hay punto único de control para transacciones, auditoría, validación.

#### Construcción de JSON Response (dispersa)

```python
# ❌ Formato inconsistente en múltiples endpoints
return jsonify({'success': True, 'ticket_id': ticket.id})
return jsonify({'success': True, 'data': {...}})
return jsonify({'success': False, 'error': '...'})
```

### 1.3 Bajo Testabilidad

**Problemas:**

1. **Acoplamiento fuerte:** Rutas directamente usan `db`, `session`, `socketio`
2. **No hay inyección de dependencias:** No puedes usar BD de test sin modificar app.py
3. **Funciones globales:** `log_audit()`, `ping_server()`, `send_teams_webhook()` acopladas a app
4. **Efectos secundarios:** No hay forma de aislar lógica de BD de WebSocket

**Ejemplo - No testeable hoy:**

```python
# En app.py
def api_create_ticket(ticket_id):
    # Mezcla: BD + HTTP request + WebSocket + email
    db.session.add(ticket)
    db.session.commit()
    emit_ticket_event(...)  # WebSocket global
    send_teams_webhook(...)  # HTTP request global
    send_email(...)  # Email global
    log_audit(...)  # BD global
    return jsonify(...)
```

Para testear `crear ticket`, necesitas:
- BD en memoria ✓ (difícil con app.py monolítico)
- Mock de WebSocket ✗ (socketio es global)
- Mock de HTTP ✗ (requests es global)
- Mock de email ✗ (smtplib es global)

### 1.4 Acoplamiento Innecesario

**Ejemplos:**

| Componente | Acoplado a | Impacto |
|------------|-----------|---------|
| Rate limiting | app global | No reutilizable en otro servidor |
| Auditoría | log_audit() global | No personalizable, no extensible |
| WebSocket | socketio global | No testeable sin app corriendo |
| Webhooks | send_teams_webhook() global | Hardcodeado Teams, no extensible |
| Email | send_email() global | No reutilizable, sin retry |
| Backup | start_backup_scheduler() | Corre automático, no parable |

### 1.5 Gestión Pobre de Configuración

**Problemas:**

1. **Constantes hardcodeadas:** Tema, colores, SLA en app.py
2. **Sin config por entorno:** No diferencia dev/test/prod
3. **Secrets en .env sin estructura:** No hay validación
4. **Config en DB pero no usada:** `Config` modelo existe pero se lee una vez

**Ejemplo:**

```python
# ❌ En app.py líneas 82–101
COMPANY_COLORS = {...}  # Hardcodeado
THEMES = {...}  # Hardcodeado

# En DB:
class Config(db.Model):
    key = db.Column(...)  # Nunca se consulta
    value = db.Column(...)
```

---

## 2. Problemas de Diseño

### 2.1 No Hay Separación de Responsabilidades

**Hoy:** 1 archivo = todo

```
app.py
├── Presentación (Flask routes)
├── Aplicación (lógica de negocio)
├── Persistencia (SQLAlchemy queries)
├── Infraestructura (WebSocket, email, backup)
└── Configuración (constantes globales)
```

**Debería ser:**

```
ticketdesk/
├── presentation/       (rutas, serialización)
├── application/        (casos de uso, orquestación)
├── domain/            (entidades, reglas de negocio)
├── infrastructure/    (BD, email, WebSocket, cache)
└── config/            (configuración)
```

### 2.2 Modelos Inflados

**Ejemplo - Ticket model (líneas 136–166):**

```python
class Ticket(db.Model):
    # 17 columnas, algunas son de presentación/cálculo
    sla_deadline = db.Column(...)
    version = db.Column(...)  # Locking optimista
    rating = db.Column(...)  # Hiper-acoplado
    time_worked_seconds = db.Column(...)  # Debería estar en otra tabla
    
    @property
    def sla_remaining(self):
        # Lógica de negocio en el modelo
        if not self.sla_deadline:
            return None
        remaining = self.sla_deadline - datetime.now()
        return max(0, int(remaining.total_seconds() / 60))
```

**Problemas:**

1. Modelo tiene lógica de cálculo que debería estar en servicio
2. Mixin de conceptos: ticket base + SLA + tiempo trabajado
3. Relaciones implícitas: `creator`, `assignee` son usuarios, pero no hay tabla de auditoría de cambios
4. Sin historial: cambios no quedan registrados (violación de requisito AUDIT TRAIL)

### 2.3 Falta de Abstracciones

**No hay:**

1. **Repository pattern:** Cada endpoint hace queries directamente (`Ticket.query.filter()`)
2. **Service layer:** Lógica de negocio dispersa en rutas
3. **DTO/Serializers:** Conversión de DB → JSON inline en cada endpoint
4. **Exception handling:** Mezcla de `jsonify({'success': False})` con excepciones globales
5. **Validación:** Sin esquema (Marshmallow, Pydantic)

**Ejemplo - Query sin abstracción (línea 758):**

```python
@app.route('/api/search', methods=['GET'])
def api_search():
    # Búsqueda hardeada, sin repositorio
    search_term = request.args.get('q', '').strip()
    # ...
    tickets = Ticket.query.filter(
        Ticket.company == session['company'],
        (Ticket.title.like(f'%{search_term}%')) | 
        (Ticket.description.like(f'%{search_term}%'))
    ).limit(50).all()
```

Sin abstracción, cada cambio en búsqueda afecta 1 lugar, pero:
- Si agregamos full-text search (FTS5), hay que tocar la ruta
- Si cambiamos de SQLite a PostgreSQL, sintaxis de búsqueda cambia
- Testing búsqueda requiere app corriendo

### 2.4 WebSocket sin Orquestación

**Hoy (líneas 1646–1668):**

```python
@socketio.on('connect')
def handle_connect():
    # ✗ Broadcast global sin segregación de empresa
    emit_ticket_event(company, event_type, ticket_data)
```

**Problemas:**

1. No hay segregación por empresa en salas
2. Broadcast manual sin patrón pub/sub
3. Difícil trackear qué usuarios están conectados
4. Sin heartbeat/timeout implementado
5. Sin reconexión automática en cliente

### 2.5 Falta de Type Hints

Todo el código es `Any`:

```python
def get_next_ticket_number(company):  # ❌ Sin tipos
def verify_jwt(token):  # ❌ Sin tipos
def assign_ticket_auto(ticket):  # ❌ Sin tipos
```

**Impacto:**
- IDEs no pueden ayudar (autocomplete no funciona)
- Bugs no detectados en type-check
- Documentación implícita en tipos perdida

---

## 3. Arquitectura Recomendada

### 3.1 Estructura de Carpetas (Clean Architecture)

```
ticketdesk/
├── __init__.py
├── main.py                              # Entry point
├── config.py                            # Configuración por entorno
│
├── domain/                              # Entidades de negocio (sin dependencias externas)
│   ├── __init__.py
│   ├── entities.py                      # Dataclasses: Ticket, User, Company, Message
│   ├── enums.py                         # TicketStatus, UserRole, Priority, etc.
│   ├── exceptions.py                    # DomainException, ValidationError
│   └── value_objects.py                 # TicketNumber, Email, etc.
│
├── application/                         # Lógica de negocio (cases de uso)
│   ├── __init__.py
│   ├── dto.py                           # DataTransferObjects: CreateTicketDTO, etc.
│   ├── services/                        # Casos de uso
│   │   ├── __init__.py
│   │   ├── ticket_service.py            # create, update, resolve, escalate, search
│   │   ├── user_service.py              # authenticate, create, manage
│   │   ├── company_service.py           # CRUD companies
│   │   ├── sla_service.py               # Calculate SLA, track deadline
│   │   ├── assignment_service.py        # Auto-assign with AI
│   │   └── audit_service.py             # Log actions, track changes
│   │
│   └── ports/                           # Interfaces (sin implementación)
│       ├── __init__.py
│       ├── ticket_repository.py         # ABC: create, update, find, search
│       ├── user_repository.py
│       ├── audit_repository.py
│       ├── email_gateway.py             # ABC: send_email(to, subject, body)
│       ├── webhook_gateway.py           # ABC: notify(event, data)
│       └── auth_provider.py             # ABC: verify_token, validate_ldap
│
├── infrastructure/                      # Implementaciones concretas
│   ├── __init__.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py                    # SQLAlchemy models
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── ticket_repository.py     # Impl TicketRepository
│   │   │   ├── user_repository.py
│   │   │   └── audit_repository.py
│   │   └── migrations/                  # Alembic migrations
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt_provider.py              # JWT handling
│   │   ├── ldap_provider.py             # LDAP/AD integration
│   │   └── password_hasher.py           # Bcrypt/PBKDF2
│   │
│   ├── email/
│   │   ├── __init__.py
│   │   └── smtp_gateway.py              # Impl EmailGateway
│   │
│   ├── webhooks/
│   │   ├── __init__.py
│   │   └── teams_gateway.py             # Impl WebhookGateway para Teams
│   │
│   ├── cache/
│   │   ├── __init__.py
│   │   └── redis_cache.py               # Opcional: Redis para JWT blacklist
│   │
│   └── monitoring/
│       ├── __init__.py
│       ├── server_monitor.py            # Health check
│       ├── backup_scheduler.py
│       └── watchdog.py
│
├── presentation/                        # HTTP/WebSocket layer
│   ├── __init__.py
│   ├── app.py                           # Factory de Flask app
│   ├── blueprints/
│   │   ├── __init__.py
│   │   ├── auth_bp.py                   # /login, /logout, /api/company-theme
│   │   ├── employee_bp.py               # /employee/* routes
│   │   ├── technician_bp.py             # /technician/* routes
│   │   ├── admin_bp.py                  # /admin/*, /api/admin/* routes
│   │   ├── api_bp.py                    # /api/* general routes (search, export, etc.)
│   │   └── health_bp.py                 # /api/health, /api/system/metrics
│   │
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── auth_middleware.py           # JWT verification
│   │   ├── rate_limit_middleware.py     # Rate limiting
│   │   ├── company_filter_middleware.py # Enforce company segregation
│   │   └── error_handler.py             # Global error handling
│   │
│   ├── websocket/
│   │   ├── __init__.py
│   │   ├── handlers.py                  # @socketio.on handlers
│   │   └── rooms.py                     # Room management by company_id
│   │
│   └── serializers/
│       ├── __init__.py
│       ├── ticket_serializer.py         # Ticket → JSON
│       ├── user_serializer.py
│       └── common_serializers.py        # Response envelopes, error formats
│
└── tests/                               # Test suite
    ├── __init__.py
    ├── conftest.py                      # Fixtures
    ├── unit/                            # Tests sin dependencias externas
    │   ├── test_ticket_service.py
    │   ├── test_user_service.py
    │   └── test_sla_service.py
    ├── integration/                     # Tests con BD test
    │   ├── test_ticket_repository.py
    │   ├── test_auth_flow.py
    │   └── test_webhooks.py
    └── e2e/                             # Tests de flujo completo
        ├── test_employee_create_ticket.py
        ├── test_technician_workflow.py
        └── test_realtime_updates.py
```

### 3.2 Flujo de Datos Limpio

```
HTTP Request
    ↓
[Presentation Layer]
  Blueprint route handler
  ↓
  Deserialize JSON → DTO
  ↓
  Middleware (auth, rate limit)
    ↓
[Application Layer]
  Service (casos de uso)
  ↓
  Validación de dominio
  ↓
[Infrastructure Layer]
  Repository (CRUD)
  ↓
  SQLAlchemy models
  ↓
  Base de datos
    ↓
Response builder
    ↓
HTTP Response

Side Effects (auditoría, webhooks, email) → Event bus
```

---

## 4. Plan de Refactoring Detallado (Phase 1-4)

### Phase 1: Preparación (Semana 1)

**Objetivo:** Preparar la base sin romper funcionalidad.

#### 1.1 Crear estructura de carpetas

```bash
mkdir -p ticketdesk/{domain,application,infrastructure,presentation,tests}
mkdir -p ticketdesk/application/{services,ports}
mkdir -p ticketdesk/infrastructure/{database/repositories,auth,email,webhooks,monitoring,cache}
mkdir -p ticketdesk/presentation/{blueprints,middlewares,websocket,serializers}
mkdir -p ticketdesk/tests/{unit,integration,e2e}
```

#### 1.2 Crear archivos stub

```python
# ticketdesk/__init__.py
# ticketdesk/config.py - Config por entorno (dev, test, prod)
# ticketdesk/domain/__init__.py
# ticketdesk/application/__init__.py
# ticketdesk/infrastructure/__init__.py
# ticketdesk/presentation/__init__.py
```

#### 1.3 Mantener app.py actual como "main.py" temporal

No eliminar app.py, copiar a `main_old.py` para referencia.

**Criterio de éxito:** Estructura lista, sin cambios en funcionalidad.

---

### Phase 2: Modelos y Persistencia (Semana 2-3)

**Objetivo:** Extraer modelos, repositories, y abstraer BD.

#### 2.1 Crear domain/entities.py

Convertir modelos SQLAlchemy a dataclasses puro (sin BD):

```python
# ticketdesk/domain/entities.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum

class TicketStatus(Enum):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'

class Priority(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

@dataclass
class Ticket:
    """Entidad de dominio: Ticket"""
    id: int
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
    # SLA
    sla_minutes: Optional[int]
    sla_deadline: Optional[datetime]
    
    @property
    def sla_remaining_minutes(self) -> Optional[int]:
        """Calcula minutos restantes de SLA."""
        if not self.sla_deadline:
            return None
        remaining = self.sla_deadline - datetime.now()
        return max(0, int(remaining.total_seconds() / 60))
    
    @property
    def is_sla_breached(self) -> bool:
        """¿SLA vencido?"""
        if not self.sla_deadline:
            return False
        return datetime.now() > self.sla_deadline

@dataclass
class User:
    id: int
    username: str
    name: str
    email: str
    role: str  # 'admin', 'technician', 'employee'
    company_id: int
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime

# ... más entities
```

#### 2.2 Crear infrastructure/database/models.py

Mantener SQLAlchemy models, pero para persistencia SOLO:

```python
# ticketdesk/infrastructure/database/models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class TicketModel(db.Model):
    """SQLAlchemy model - solo para BD"""
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True)
    # ... columnas
    
    # Mapper a domain entity
    def to_domain(self) -> Ticket:
        return Ticket(
            id=self.id,
            ticket_number=self.ticket_number,
            # ...
        )
    
    @staticmethod
    def from_domain(ticket: Ticket) -> 'TicketModel':
        return TicketModel(
            id=ticket.id,
            ticket_number=ticket.ticket_number,
            # ...
        )
```

#### 2.3 Crear application/ports/ (Interfaces)

```python
# ticketdesk/application/ports/ticket_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities import Ticket

class TicketRepository(ABC):
    """Interfaz para persistencia de tickets"""
    
    @abstractmethod
    def create(self, ticket: Ticket) -> int:
        """Crea ticket, retorna ID"""
        pass
    
    @abstractmethod
    def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        """Obtiene ticket por ID"""
        pass
    
    @abstractmethod
    def list_by_company(self, company_id: int) -> List[Ticket]:
        """Listar todos los tickets de una empresa"""
        pass
    
    @abstractmethod
    def search(self, company_id: int, query: str) -> List[Ticket]:
        """Búsqueda de texto completo"""
        pass
    
    @abstractmethod
    def update(self, ticket: Ticket) -> bool:
        """Actualiza ticket (versioning optimista)"""
        pass
```

#### 2.4 Crear infrastructure/database/repositories/

```python
# ticketdesk/infrastructure/database/repositories/ticket_repository.py
from application.ports.ticket_repository import TicketRepository
from domain.entities import Ticket
from infrastructure.database.models import TicketModel, db

class SQLiteTicketRepository(TicketRepository):
    """Implementación SQLite de TicketRepository"""
    
    def create(self, ticket: Ticket) -> int:
        model = TicketModel.from_domain(ticket)
        db.session.add(model)
        db.session.commit()
        return model.id
    
    def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        model = TicketModel.query.get(ticket_id)
        return model.to_domain() if model else None
    
    # ... más métodos
```

**Beneficios:**
- Si cambias de SQLite a PostgreSQL, solo cambias implementación
- Fácil hacer mock para tests (crear repo en memoria)
- Lógica de negocio separada de detalles de persistencia

#### 2.5 Setup de tests

```python
# ticketdesk/tests/conftest.py
import pytest
from ticketdesk.infrastructure.database.models import db

@pytest.fixture
def app():
    """Flask app para tests"""
    app = create_app(config_class=TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def mock_ticket_repo():
    """Repository en memoria para tests unitarios"""
    return InMemoryTicketRepository()
```

**Criterio de éxito:**
- Modelos extraídos a domain/
- Repositories abstractos en ports/
- Implementaciones concretas en infrastructure/
- 5+ tests unitarios pasando

---

### Phase 3: Application Layer (Semana 3-4)

**Objetivo:** Extraer lógica de negocio de rutas a servicios.

#### 3.1 Crear application/services/

```python
# ticketdesk/application/services/ticket_service.py
from application.ports.ticket_repository import TicketRepository
from application.dto import CreateTicketDTO, UpdateTicketDTO
from domain.entities import Ticket, TicketStatus
from domain.exceptions import TicketNotFoundError, ValidationError

class TicketService:
    """Casos de uso para tickets"""
    
    def __init__(self, ticket_repo: TicketRepository, 
                 audit_repo: AuditRepository,
                 sla_service: 'SLAService'):
        self.ticket_repo = ticket_repo
        self.audit_repo = audit_repo
        self.sla_service = sla_service
    
    def create_ticket(self, dto: CreateTicketDTO, user_id: int) -> Ticket:
        """RF-01-02: Crear nuevo ticket"""
        
        # Validar entrada
        if not dto.title or len(dto.title) > 200:
            raise ValidationError("Title required, max 200 chars")
        
        if len(dto.description) < 10:
            raise ValidationError("Description too short")
        
        # Crear entidad de dominio
        ticket = Ticket(
            id=None,  # Se genera en BD
            ticket_number=self.ticket_repo.next_number(dto.company_id),
            title=dto.title,
            description=dto.description,
            status=TicketStatus.OPEN,
            priority=dto.priority,
            company_id=dto.company_id,
            creator_id=user_id,
            assignee_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            resolved_at=None,
            version=1,
            sla_minutes=None,
            sla_deadline=None,
        )
        
        # Calcular SLA
        sla_deadline = self.sla_service.calculate_deadline(
            priority=ticket.priority,
            company_id=ticket.company_id
        )
        ticket.sla_deadline = sla_deadline
        ticket.sla_minutes = self.sla_service.minutes_to_deadline(sla_deadline)
        
        # Persistir
        ticket_id = self.ticket_repo.create(ticket)
        ticket.id = ticket_id
        
        # Auditar
        self.audit_repo.log(
            action='ticket_created',
            user_id=user_id,
            entity_type='ticket',
            entity_id=ticket_id,
            description=f'Ticket {ticket.ticket_number} creado'
        )
        
        return ticket
    
    def resolve_ticket(self, ticket_id: int, resolution: str, user_id: int) -> Ticket:
        """RF-01-05: Resolver ticket"""
        
        ticket = self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found")
        
        # Validación de negocio
        if ticket.status == TicketStatus.RESOLVED:
            raise ValidationError("Ticket already resolved")
        
        # Cambiar estado
        ticket.status = TicketStatus.RESOLVED
        ticket.resolved_at = datetime.now()
        ticket.version += 1
        
        # Persistir (con versionning optimista)
        if not self.ticket_repo.update(ticket):
            raise ValidationError("Conflict: ticket was modified, try again")
        
        # Auditar
        self.audit_repo.log(
            action='ticket_resolved',
            user_id=user_id,
            entity_type='ticket',
            entity_id=ticket_id,
            description=f'Ticket {ticket.ticket_number} resuelto'
        )
        
        return ticket
    
    def search(self, company_id: int, query: str) -> List[Ticket]:
        """Búsqueda de texto completo"""
        if len(query) < 3:
            raise ValidationError("Search query too short")
        
        return self.ticket_repo.search(company_id, query)
```

#### 3.2 Inyección de Dependencias

```python
# ticketdesk/presentation/app.py
from flask import Flask
from application.services.ticket_service import TicketService
from infrastructure.database.repositories.ticket_repository import SQLiteTicketRepository

def create_app(config_class=None):
    app = Flask(__name__)
    
    # Infraestructura
    db.init_app(app)
    ticket_repo = SQLiteTicketRepository(db)
    audit_repo = SQLiteAuditRepository(db)
    
    # Servicios (inyectar dependencias)
    ticket_service = TicketService(ticket_repo, audit_repo, sla_service)
    user_service = UserService(user_repo, auth_provider)
    
    # Guardar en app context
    app.ticket_service = ticket_service
    app.user_service = user_service
    
    # Blueprints (reciben servicios)
    from presentation.blueprints.employee_bp import employee_bp
    app.register_blueprint(
        employee_bp,
        url_prefix='/employee',
        ticket_service=ticket_service
    )
    
    return app
```

**Criterio de éxito:**
- TicketService con casos de uso clave
- Servicios sin dependencia de Flask/request
- 15+ tests unitarios (servicios sin BD)

---

### Phase 4: Presentation Layer - Blueprints (Semana 4+)

**Objetivo:** Convertir rutas a blueprints, usar servicios.

#### 4.1 Crear blueprints/auth_bp.py

```python
# ticketdesk/presentation/blueprints/auth_bp.py
from flask import Blueprint, render_template, request, jsonify, session, redirect
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def require_auth(f):
    """Decorator: verificar JWT en session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator: verificar role admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    # POST: Procesar login
    user_service = current_app.user_service
    
    try:
        user, token = user_service.authenticate(
            username=request.form.get('username'),
            password=request.form.get('password'),
            company=request.form.get('company')
        )
        
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session['company'] = user.company
        
        return redirect(f'/{user.role}/dashboard')
    
    except AuthenticationError as e:
        return jsonify({'success': False, 'error': str(e)}), 401

@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    user_service = current_app.user_service
    user_service.logout(session['user_id'])
    session.clear()
    return jsonify({'success': True})
```

#### 4.2 Crear blueprints/employee_bp.py

```python
# ticketdesk/presentation/blueprints/employee_bp.py
from flask import Blueprint, render_template, request, jsonify, session
from application.dto import CreateTicketDTO
from application.exceptions import ValidationError
from presentation.serializers import TicketSerializer

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/dashboard')
@require_auth
def dashboard():
    """RF-01-01: Dashboard de empleado"""
    ticket_service = current_app.ticket_service
    
    # Obtener tickets del usuario (como creador)
    tickets = ticket_service.list_my_tickets(
        user_id=session['user_id'],
        company_id=session['company_id']
    )
    
    # Serializar a JSON
    serializer = TicketSerializer()
    data = [serializer.dump(t) for t in tickets]
    
    return render_template('employee/dashboard.html', tickets=data)

@employee_bp.route('/create', methods=['GET', 'POST'])
@require_auth
def create_ticket():
    """RF-01-02: Crear nuevo ticket"""
    
    if request.method == 'GET':
        return render_template('employee/create.html')
    
    # POST: Procesar creación
    ticket_service = current_app.ticket_service
    
    try:
        dto = CreateTicketDTO(
            title=request.form.get('title'),
            description=request.form.get('description'),
            category=request.form.get('category'),
            priority=request.form.get('priority', 'medium'),
            company_id=session['company_id']
        )
        
        ticket = ticket_service.create_ticket(dto, session['user_id'])
        
        # Emitir evento realtime (WebSocket)
        socketio.emit('ticket_created', 
                     TicketSerializer().dump(ticket),
                     room=f"company_{session['company_id']}")
        
        return jsonify({'success': True, 'ticket_id': ticket.id})
    
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 422

@employee_bp.route('/ticket/<int:ticket_id>')
@require_auth
def view_ticket(ticket_id):
    """RF-01-03: Ver detalles de ticket"""
    ticket_service = current_app.ticket_service
    
    ticket = ticket_service.get_ticket(ticket_id, session['user_id'])
    if not ticket:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    
    # Verificar permiso: solo si es creador
    if ticket.creator_id != session['user_id']:
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    
    return render_template('employee/ticket.html', 
                         ticket=TicketSerializer().dump(ticket))
```

#### 4.3 Crear blueprints/admin_bp.py

```python
# ticketdesk/presentation/blueprints/admin_bp.py
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@require_auth
@require_admin
def dashboard():
    """RF-02-01: Admin dashboard con métricas"""
    # ...

@admin_bp.route('/api/companies', methods=['GET', 'POST'])
@require_auth
@require_admin
def manage_companies():
    """RF-02-02: CRUD de empresas"""
    company_service = current_app.company_service
    
    if request.method == 'GET':
        companies = company_service.list_all()
        return jsonify({'success': True, 'companies': [...]})
    
    # POST: Crear empresa
    # ...
```

#### 4.4 Registrar todos los blueprints

```python
# ticketdesk/presentation/app.py
def create_app(config_class=None):
    app = Flask(__name__)
    # ... setup
    
    # Registrar blueprints
    from presentation.blueprints import (
        auth_bp, employee_bp, technician_bp, admin_bp, api_bp, health_bp
    )
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp, url_prefix='/employee')
    app.register_blueprint(technician_bp, url_prefix='/technician')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(health_bp, url_prefix='/api')
    
    return app
```

**Criterio de éxito:**
- 6 blueprints creados
- Rutas ≤30 líneas (usan servicios)
- Error handling centralizado

---

### Phase 5: Infrastructure - Auth, Email, Webhooks (Semana 5)

**Objetivo:** Abstraer integraciones externas.

#### 5.1 Auth providers

```python
# ticketdesk/infrastructure/auth/jwt_provider.py
class JWTProvider:
    def generate_token(self, user_id: int, company_id: int) -> str:
        jti = str(uuid.uuid4())
        payload = {...}
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256'), jti
    
    def verify_token(self, token: str) -> Dict:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            # Verificar blacklist
            if self.blacklist_repo.is_blacklisted(payload['jti']):
                return None
            return payload
        except:
            return None
    
    def revoke_token(self, jti: str):
        self.blacklist_repo.add(jti, expiry_time)
```

#### 5.2 Email gateway

```python
# ticketdesk/infrastructure/email/smtp_gateway.py
class SMTPEmailGateway:
    def send_email(self, to: str, subject: str, body: str, 
                  html: Optional[str] = None) -> bool:
        # Implementar reintento con backoff exponencial
        # Logging de entrega
        pass
```

#### 5.3 Webhook gateway

```python
# ticketdesk/infrastructure/webhooks/teams_gateway.py
class TeamsWebhookGateway:
    def notify(self, event: str, ticket: Ticket) -> bool:
        webhooks = self.webhook_repo.find_by_event(event)
        for webhook in webhooks:
            self._send_notification(webhook, ticket)
```

**Criterio de éxito:**
- Auth abstraída (fácil cambiar de JWT a OAuth)
- Email abstraído (fácil cambiar de SMTP a AWS SES)
- Webhooks abstraídos (agregar Slack sin tocar aplicación)

---

### Phase 6: WebSocket Refactor (Semana 6)

**Objetivo:** Salas segregadas por empresa, heartbeat, manejo de desconexión.

```python
# ticketdesk/presentation/websocket/handlers.py
from flask_socketio import socketio, emit, join_room, leave_room

@socketio.on('connect')
def on_connect():
    """Conectar usuario a sala de su empresa"""
    if 'user_id' not in session:
        return False
    
    user_id = session['user_id']
    company_id = session['company_id']
    room = f"company_{company_id}"
    
    join_room(room)
    
    # Registrar sesión activa
    session_service = current_app.session_service
    session_service.register_ws_session(user_id, request.sid)
    
    emit('connected', {'message': 'Conectado'})

@socketio.on('disconnect')
def on_disconnect():
    user_id = session.get('user_id')
    session_service = current_app.session_service
    session_service.unregister_ws_session(user_id)

# Event bus para ticket changes
def on_ticket_created(ticket: Ticket):
    data = TicketSerializer().dump(ticket)
    socketio.emit('ticket_created', data, 
                 room=f"company_{ticket.company_id}")

def on_ticket_updated(ticket: Ticket):
    data = TicketSerializer().dump(ticket)
    socketio.emit('ticket_updated', data,
                 room=f"company_{ticket.company_id}")
```

**Criterio de éxito:**
- Salas por empresa
- Heartbeat implementado
- Reconexión automática

---

### Phase 7: Análisis y Optimización Final (Semana 7-8)

**Objetivo:** Benchmarking, testing, documentación.

#### 7.1 Performance testing

```bash
pytest --benchmark tests/benchmark_ticket_search.py
# Esperar: <200ms para búsqueda de 1M tickets
```

#### 7.2 Coverage

```bash
pytest --cov=ticketdesk tests/
# Esperar: >80% para servicios, >70% global
```

#### 7.3 Documentación

- API docs (OpenAPI)
- Decisiones de diseño (ADRs)
- Guía de contribución

---

## 5. Archivos a Crear

| Archivo | Líneas | Propósito |
|---------|--------|----------|
| `ticketdesk/config.py` | 50 | Config por entorno |
| `ticketdesk/domain/entities.py` | 300 | Dataclasses de dominio |
| `ticketdesk/domain/enums.py` | 100 | Enumeraciones |
| `ticketdesk/domain/exceptions.py` | 50 | Excepciones custom |
| `ticketdesk/domain/value_objects.py` | 100 | VO: Email, TicketNumber, etc. |
| `ticketdesk/application/dto.py` | 150 | Data transfer objects |
| `ticketdesk/application/ports/*.py` | 500 | Interfaces (6 archivos) |
| `ticketdesk/application/services/*.py` | 800 | Servicios (8 archivos) |
| `ticketdesk/infrastructure/database/models.py` | 300 | SQLAlchemy models |
| `ticketdesk/infrastructure/database/repositories/*.py` | 600 | Impl (6 archivos) |
| `ticketdesk/infrastructure/auth/*.py` | 300 | JWT, LDAP, password |
| `ticketdesk/infrastructure/email/*.py` | 150 | SMTP gateway |
| `ticketdesk/infrastructure/webhooks/*.py` | 150 | Teams, Slack, etc. |
| `ticketdesk/infrastructure/monitoring/*.py` | 250 | Watchdog, backup, monitor |
| `ticketdesk/presentation/app.py` | 100 | Factory de Flask |
| `ticketdesk/presentation/blueprints/*.py` | 800 | 6 blueprints |
| `ticketdesk/presentation/middlewares/*.py` | 300 | Auth, rate limit, error |
| `ticketdesk/presentation/websocket/*.py` | 150 | Socket.IO handlers |
| `ticketdesk/presentation/serializers/*.py` | 300 | JSON serialization |
| `ticketdesk/tests/*.py` | 1000+ | Tests unitarios e integración |
| **TOTAL** | **7,800+** | Código refactorizado |

---

## 6. Archivos a Eliminar / Mover

| Archivo Actual | Acción | Razón |
|---|---|---|
| `app.py` (1,632 líneas) | Separar en 20+ archivos | Demasiado monolítico |
| `main_old.py` | Copiar para referencia | Mantener histórico |
| Constantes hardcodeadas | Mover a `config.py` | Mejor configuración |
| Queries inline | Mover a repositories | Abstracción de persistencia |
| Lógica en rutas | Mover a servicios | Separación de capas |

---

## 7. Dependencias Nuevas

```
pydantic==2.5.0          # Validación de DTO
marshmallow==3.20.0      # Serialización
python-dotenv==1.0.0     # Config desde .env
alembic==1.13.0          # Migraciones DB
pytest==7.4.0            # Testing
pytest-cov==4.1.0        # Coverage
pytest-mock==3.12.0      # Mocking
factory-boy==3.3.0       # Fixtures
coverage==7.3.0          # Coverage reporting
```

---

## 8. Tabla de Comparación: Antes vs Después

| Aspecto | Antes | Después | Mejora |
|---------|-------|---------|--------|
| **Tamaño main** | 1,632 líneas | <100 líneas | ✓✓✓ |
| **Duplicación auth** | 23 repeticiones | 1 decorator | ✓✓✓ |
| **DB queries** | 41 inline | Repositorio central | ✓✓✓ |
| **Testabilidad** | No (acoplado) | Alta (inyección DI) | ✓✓✓ |
| **Tipo hints** | 0% | 100% | ✓✓✓ |
| **Composición** | Monolítica | Modular | ✓✓✓ |
| **Extensibilidad** | Baja | Alta (SOLID) | ✓✓✓ |
| **Performance** | N/A | Igual | ✓ |
| **Lines of code** | 1,632 | 7,800+ | ✗ (Pero estructurado) |

---

## 9. Riesgos y Mitigación

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|-----------|
| Regresiones durante refactor | Alta | Tests E2E antes de cambios |
| Incompletitud de specs | Media | Revisar CLAUDE.md, RF* |
| Performance degradation | Baja | Benchmarking en Phase 7 |
| Equipo no adopta arquitectura | Media | Documentación + pair programming |
| DB migrations | Media | Alembic setup en Phase 2 |

---

## 10. Próximos Pasos

1. **Aceptar plan** - Este documento
2. **Setup inicial** - Phase 1 (crear carpetas)
3. **Extraer modelos** - Phase 2 (entities, repositories)
4. **Implement services** - Phase 3 (lógica de negocio)
5. **Blueprints** - Phase 4 (rutas refactorizadas)
6. **Infrastructure** - Phase 5 (auth, email, webhooks)
7. **Testing** - Phase 6 (cobertura >80%)
8. **Documentation** - Phase 7 (API docs, ADRs)

---

## Conclusión

El refactoring a una arquitectura limpia (Clean Architecture / Hexagonal Architecture) requiere **~8 semanas** pero resultará en:

✓ Código 10x más mantenible  
✓ Testing sin mocking complejo  
✓ Cambios aislados (1 feature = cambios en 1 lugar)  
✓ Onboarding de nuevos devs/agentes más fácil  
✓ Escalabilidad sin reescritura total  

**Costo:** 7,800+ líneas de código (pero bien estructuradas)  
**Beneficio:** Mantenibilidad, testabilidad, extensibilidad a largo plazo
