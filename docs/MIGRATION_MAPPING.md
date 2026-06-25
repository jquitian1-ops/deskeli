# Matriz de Migración: app.py → Clean Architecture

**Propósito:** Mapeo visual de dónde va cada componente de app.py en la nueva arquitectura

---

## 1. Imports (líneas 1-30)

| Item | Línea | Destino | Motivo |
|------|-------|---------|--------|
| Flask imports | 7-8 | `presentation/app.py` | Factory de app |
| SQLAlchemy | 9 | `infrastructure/database/models.py` | ORM |
| SocketIO | 10 | `presentation/websocket/handlers.py` | Real-time events |
| jwt | 13 | `infrastructure/auth/jwt_provider.py` | Token handling |
| requests | 20 | `infrastructure/webhooks/` | HTTP calls |
| threading | 21 | `infrastructure/monitoring/` | Daemons |
| smtplib | 28 | `infrastructure/email/smtp_gateway.py` | Envío de emails |

---

## 2. Configuración Global (líneas 32-101)

| Item | Línea | Destino | Cambio |
|------|-------|---------|--------|
| RATE_LIMIT | 37 | `config.py` | Env var |
| COMPANY_COLORS | 82-86 | `infrastructure/database/models.py` (seed) | BD |
| THEMES | 88-101 | `infrastructure/database/models.py` (seed) | BD |

---

## 3. Modelos SQLAlchemy (líneas 107-250)

| Modelo | Línea | Domain Entity | SQLAlchemy Model | Repository |
|--------|-------|---------------|------------------|------------|
| Company | 107 | `domain/entities.py:Company` | `infrastructure/database/models.py:CompanyModel` | `infrastructure/database/repositories/company_repository.py` |
| User | 122 | `domain/entities.py:User` | `infrastructure/database/models.py:UserModel` | `infrastructure/database/repositories/user_repository.py` |
| Ticket | 136 | `domain/entities.py:Ticket` | `infrastructure/database/models.py:TicketModel` | `infrastructure/database/repositories/ticket_repository.py` |
| Message | 167 | `domain/entities.py:Message` | `infrastructure/database/models.py:MessageModel` | `infrastructure/database/repositories/message_repository.py` |
| TokenBlacklist | 176 | `domain/entities.py:TokenBlacklist` | `infrastructure/database/models.py:TokenBlacklistModel` | `infrastructure/database/repositories/token_blacklist_repository.py` |
| AuditLog | 182 | `domain/entities.py:AuditLog` | `infrastructure/database/models.py:AuditLogModel` | `infrastructure/database/repositories/audit_repository.py` |
| Config | 193 | `domain/entities.py:Config` | `infrastructure/database/models.py:ConfigModel` | `infrastructure/database/repositories/config_repository.py` |
| Template | 200 | `domain/entities.py:Template` | `infrastructure/database/models.py:TemplateModel` | `infrastructure/database/repositories/template_repository.py` |
| Server | 213 | `domain/entities.py:Server` | `infrastructure/database/models.py:ServerModel` | `infrastructure/database/repositories/server_repository.py` |
| UserSession | 223 | `domain/entities.py:UserSession` | `infrastructure/database/models.py:UserSessionModel` | `infrastructure/database/repositories/session_repository.py` |
| BotKnowledge | 233 | `domain/entities.py:BotKnowledge` | `infrastructure/database/models.py:BotKnowledgeModel` | `infrastructure/database/repositories/bot_repository.py` |
| Webhook | 243 | `domain/entities.py:Webhook` | `infrastructure/database/models.py:WebhookModel` | `infrastructure/database/repositories/webhook_repository.py` |

---

## 4. Funciones Utilidad (líneas 252-320)

| Función | Línea | Destino | Tipo |
|---------|-------|---------|------|
| `rate_limit_check()` | 40 | `presentation/middlewares/rate_limit_middleware.py` | Middleware |
| `get_next_ticket_number()` | 256 | `application/services/ticket_service.py` | Service method |
| `generate_jwt()` | 262 | `infrastructure/auth/jwt_provider.py` | Auth provider |
| `verify_jwt()` | 274 | `infrastructure/auth/jwt_provider.py` | Auth provider |
| `log_audit()` | 288 | `application/services/audit_service.py` | Service method |

---

## 5. Rutas HTTP (líneas 310+)

### Authentication (5 rutas)

| Ruta | Método | Línea | Destino Blueprint | Service |
|------|--------|-------|-------------------|---------|
| `/` | GET | 310 | `presentation/blueprints/auth_bp.py` | `application/services/user_service.py` |
| `/login` | GET,POST | 323 | `presentation/blueprints/auth_bp.py` | `application/services/user_service.py` |
| `/api/company-theme` | GET | 360 | `presentation/blueprints/auth_bp.py` | `application/services/company_service.py` |
| `/theme.css` | GET | 380 | `presentation/blueprints/auth_bp.py` | (CSS generator) |
| `/logout` | POST | 432 | `presentation/blueprints/auth_bp.py` | `application/services/user_service.py` |

### Companies (3 rutas)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/companies` | GET | 444 | `presentation/blueprints/api_bp.py` | `application/services/company_service.py` |
| `/api/company/<code>` | GET | 457 | `presentation/blueprints/api_bp.py` | `application/services/company_service.py` |
| `/api/admin/companies` | GET,POST | 475,494 | `presentation/blueprints/admin_bp.py` | `application/services/company_service.py` |
| `/api/admin/companies/<id>` | PUT | 520 | `presentation/blueprints/admin_bp.py` | `application/services/company_service.py` |

### Employee Portal (4 rutas)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/employee/dashboard` | GET | 571 | `presentation/blueprints/employee_bp.py` | `application/services/ticket_service.py` |
| `/employee/create` | GET,POST | 596 | `presentation/blueprints/employee_bp.py` | `application/services/ticket_service.py` |
| `/employee/ticket/<id>` | GET | 629 | `presentation/blueprints/employee_bp.py` | `application/services/ticket_service.py` |

### Technician Portal (2 rutas)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/technician/dashboard` | GET | 640 | `presentation/blueprints/technician_bp.py` | `application/services/ticket_service.py` |

### Admin Portal (2 rutas)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/admin/dashboard` | GET | 658 | `presentation/blueprints/admin_bp.py` | `application/services/report_service.py` |
| `/admin/themes` | GET | 696 | `presentation/blueprints/admin_bp.py` | `application/services/company_service.py` |

### Health & Monitoring (2 rutas)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/health` | GET | 706 | `presentation/blueprints/health_bp.py` | `application/services/health_service.py` |
| `/api/system/metrics` | GET | 1842 | `presentation/blueprints/health_bp.py` | `application/services/metrics_service.py` |

### Bot (1 ruta)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/bot/ask` | POST | 715 | `presentation/blueprints/api_bp.py` | `application/services/bot_service.py` |

### Search (1 ruta)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/search` | GET | 757 | `presentation/blueprints/api_bp.py` | `application/services/ticket_service.py` |

### Export (2 rutas)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/export/excel` | GET | 784 | `presentation/blueprints/api_bp.py` | `application/services/export_service.py` |
| `/api/export/csv` | GET | 832 | `presentation/blueprints/api_bp.py` | `application/services/export_service.py` |

### Config (1 ruta)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/config/sla` | POST | 871 | `presentation/blueprints/admin_bp.py` | `application/services/sla_service.py` |
| `/api/config/theme` | POST | 892 | `presentation/blueprints/admin_bp.py` | `application/services/company_service.py` |

### Webhooks (3 rutas)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/admin/webhooks` | GET,POST | 1503,1519 | `presentation/blueprints/admin_bp.py` | `application/services/webhook_service.py` |
| `/api/admin/webhooks/<id>` | DELETE | 1540 | `presentation/blueprints/admin_bp.py` | `application/services/webhook_service.py` |

### Servers (3 rutas)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/admin/servers` | GET,POST | 1591,1607 | `presentation/blueprints/admin_bp.py` | `application/services/server_service.py` |
| `/api/admin/servers/<id>` | DELETE | 1626 | `presentation/blueprints/admin_bp.py` | `application/services/server_service.py` |

### Sessions (2 rutas)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/admin/sessions` | GET | 1467 | `presentation/blueprints/admin_bp.py` | `application/services/session_service.py` |
| `/api/admin/sessions/<id>/kick` | POST | 1486 | `presentation/blueprints/admin_bp.py` | `application/services/session_service.py` |

### Tickets (6 rutas)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/admin/tickets/create` | POST | 1293 | `presentation/blueprints/admin_bp.py` | `application/services/ticket_service.py` |
| `/api/admin/tickets/<id>/edit` | POST | 1339 | `presentation/blueprints/admin_bp.py` | `application/services/ticket_service.py` |
| `/api/admin/tickets/<id>/delete` | POST | 1362 | `presentation/blueprints/admin_bp.py` | `application/services/ticket_service.py` |
| `/api/ticket/<id>/time` | GET,POST | 1679,1755 | `presentation/blueprints/api_bp.py` | `application/services/ticket_service.py` |
| `/api/ticket/<id>/rating` | POST | 1722 | `presentation/blueprints/api_bp.py` | `application/services/ticket_service.py` |
| `/api/ticket/<id>/reassign` | POST | 1790 | `presentation/blueprints/api_bp.py` | `application/services/ticket_service.py` |
| `/api/ticket/<id>/escalate` | POST | 1928 | `presentation/blueprints/api_bp.py` | `application/services/sla_service.py` |

### Templates (1 ruta)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/templates` | GET | 1383 | `presentation/blueprints/api_bp.py` | `application/services/template_service.py` |

### Reports (1 ruta)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/reports/dashboard` | GET | 1403 | `presentation/blueprints/admin_bp.py` | `application/services/report_service.py` |

### Filters (1 ruta)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/tickets/filter` | POST | 1881 | `presentation/blueprints/api_bp.py` | `application/services/ticket_service.py` |

### History (1 ruta)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/ticket/<id>/history` | GET | 1695 | `presentation/blueprints/api_bp.py` | `application/services/audit_service.py` |

### SLA (1 ruta)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/escalate-sla` | POST | 1440 | `presentation/blueprints/api_bp.py` | `application/services/sla_service.py` |

### Push Notifications (1 ruta)

| Ruta | Método | Línea | Destino | Service |
|------|--------|-------|---------|---------|
| `/api/notifications/push-subscribe` | POST | 1821 | `presentation/blueprints/api_bp.py` | `application/services/notification_service.py` |

**TOTAL RUTAS:** 40+ → Distribuidas en 6 blueprints

---

## 6. Funciones de Negocio (líneas 920-1100)

| Función | Línea | Destino | Tipo |
|---------|-------|---------|------|
| `ping_server()` | 920 | `application/services/server_service.py` | Service method |
| `assign_ticket_auto()` | 965 | `application/services/assignment_service.py` | Service method |
| `start_server_monitoring()` | 1000 | `infrastructure/monitoring/server_monitor.py` | Daemon |
| `create_backup()` | 1020 | `infrastructure/monitoring/backup_scheduler.py` | Daemon |
| `start_backup_scheduler()` | 1049 | `infrastructure/monitoring/backup_scheduler.py` | Daemon |
| `send_email()` | 1075 | `infrastructure/email/smtp_gateway.py` | Gateway |
| `start_watchdog()` | 1102 | `infrastructure/monitoring/watchdog.py` | Daemon |

---

## 7. Inicialización de BD (línea 1133)

| Componente | Línea | Destino | Tipo |
|-----------|-------|---------|------|
| `init_db()` | 1133 | `presentation/app.py` (factory) | Setup |
| Schema creation | 1136 | `infrastructure/database/models.py` | ORM |
| Seed data | 1139+ | `infrastructure/database/seeds/` | Script |
| Default configs | 1226+ | `infrastructure/database/seeds/` | Script |

---

## 8. WebSocket (líneas 1646-1668)

| Handler | Línea | Destino | Cambio |
|---------|-------|---------|--------|
| `@socketio.on('connect')` | 1646 | `presentation/websocket/handlers.py` | Agregar room management |
| `@socketio.on('disconnect')` | 1660 | `presentation/websocket/handlers.py` | Limpiar sesión |
| `emit_ticket_event()` | 1668 | `presentation/websocket/emitters.py` | Event emitter |

---

## 9. Resumen de Archivos a Crear

### Domain Layer (5 archivos)
```
ticketdesk/domain/
├── __init__.py
├── entities.py          (400 líneas) - 10 dataclasses
├── enums.py             (100 líneas) - TicketStatus, Priority, etc.
├── exceptions.py        (50 líneas) - DomainException, ValidationError, etc.
└── value_objects.py     (100 líneas) - Email, TicketNumber, etc.
```

### Application Layer (20+ archivos)
```
ticketdesk/application/
├── __init__.py
├── dto.py               (150 líneas) - DTOs
├── ports/               (6 archivos, 500 líneas total) - Interfaces
│   ├── ticket_repository.py
│   ├── user_repository.py
│   ├── company_repository.py
│   ├── audit_repository.py
│   ├── email_gateway.py
│   └── auth_provider.py
└── services/            (8 archivos, 800 líneas total) - Casos de uso
    ├── ticket_service.py
    ├── user_service.py
    ├── company_service.py
    ├── sla_service.py
    ├── assignment_service.py
    ├── audit_service.py
    ├── export_service.py
    └── notification_service.py
```

### Infrastructure Layer (25+ archivos)
```
ticketdesk/infrastructure/
├── database/
│   ├── models.py        (300 líneas) - SQLAlchemy models
│   ├── migrations/      - Alembic migrations
│   ├── repositories/    (6 archivos, 600 líneas) - CRUD implementations
│   └── seeds/           - Initial data
├── auth/
│   ├── jwt_provider.py  (100 líneas)
│   ├── ldap_provider.py (100 líneas)
│   └── password_hasher.py (50 líneas)
├── email/
│   └── smtp_gateway.py  (100 líneas)
├── webhooks/
│   └── teams_gateway.py (150 líneas)
├── cache/
│   └── redis_cache.py   (100 líneas)
└── monitoring/
    ├── server_monitor.py (150 líneas)
    ├── backup_scheduler.py (150 líneas)
    └── watchdog.py      (100 líneas)
```

### Presentation Layer (15+ archivos)
```
ticketdesk/presentation/
├── __init__.py
├── app.py               (100 líneas) - Flask factory
├── blueprints/          (6 archivos, 800 líneas)
│   ├── auth_bp.py
│   ├── employee_bp.py
│   ├── technician_bp.py
│   ├── admin_bp.py
│   ├── api_bp.py
│   └── health_bp.py
├── middlewares/         (4 archivos, 300 líneas)
│   ├── auth_middleware.py
│   ├── rate_limit_middleware.py
│   ├── error_handler.py
│   └── company_filter.py
├── websocket/           (2 archivos, 200 líneas)
│   ├── handlers.py
│   └── emitters.py
└── serializers/         (4 archivos, 300 líneas)
    ├── ticket_serializer.py
    ├── user_serializer.py
    ├── company_serializer.py
    └── common_serializers.py
```

---

## 10. Resumen de Cambios

| Categoría | De | A | Cambio |
|-----------|----|----|--------|
| Archivos Python | 1 (monolítico) | 70+ (modular) | +69 |
| Líneas código | 1,632 | 7,800+ | +6,168 |
| Pero líneas por archivo | 1,632 (promedio) | <100 (promedio) | ✓ |
| Duplicación auth | 23 lugares | 1 decorator | -22 |
| Duplicación DB | 41 inline | 1 patrón repository | -40 |
| Type hints | 0% | 100% | ✓ |
| Tests unitarios | <10 | 50+ | ✓ |
| Blueprints | 0 | 6 | ✓ |
| Servicios | Dispersos | 8+ centralizados | ✓ |
| Repositories | Inexistentes | 6+ implementados | ✓ |

---

## Notas Finales

### Lo que NO cambia
- ✓ Comportamiento API (mismo JSON, mismos endpoints)
- ✓ BD (mismo esquema SQLite/PostgreSQL)
- ✓ Requisitos funcionales (RF-01, RF-02, etc.)
- ✓ Performance (equivalente o mejor)

### Lo que SÍ cambia
- ✓ Estructura interna (limpia, modular)
- ✓ Type hints (100%)
- ✓ Testabilidad (fácil)
- ✓ Mantenibilidad (alto)
- ✓ Extensibilidad (plugins sin tocar core)

### Cómo validar
1. Tests E2E pasan (funcionalidad preservada)
2. Benchmarks (performance ≥ original)
3. Coverage >80% (servicios testados)
4. Type checking `mypy` sin errores
5. Zero security regressions
