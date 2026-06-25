# ADR-001: Refactoring a Clean Architecture (Hexagonal/Ports-Adapters)

## Status
**PROPOSED** (Pending stakeholder approval)

## Date
2026-05-29

## Context

### Current State
The TicketDesk application has grown to a monolithic Flask file (`app.py`, 1,632 lines) containing:
- 10 SQLAlchemy models
- 40+ HTTP routes
- Core business logic (SLA, auto-assignment, webhooks)
- Infrastructure concerns (rate limiting, email, backup, monitoring)
- All mixed in a single file

### Problems This Creates

#### 1. High Cognitive Load
Adding a single feature requires understanding and modifying code scattered across 1,632 lines. Example: Creating a ticket touches:
- 3 routes (employee create, admin create, template create)
- 2 models (Ticket, Message)
- 3+ utility functions (log_audit, emit_ticket_event, send_teams_webhook)
- Database operations inline in each route
- No clear separation of concerns

#### 2. Code Duplication
- **23 instances** of `if 'user_id' not in session or session['role'] != 'admin'`
- **41 instances** of `db.session.add()` / `db.session.commit()` without abstraction
- **6+ custom JSON response builders** with inconsistent formats

**Impact:** A single bug fix (e.g., auth check) requires changes in 23 places. Risk of inconsistency is high.

#### 3. Poor Testability
Current architecture couples:
- HTTP request handling (Flask routes)
- Database operations (SQLAlchemy)
- Real-time events (Socket.IO)
- External services (email, webhooks, LDAP)

**Example:** To unit test "create ticket" business logic, you must:
1. Create a Flask test client
2. Set up a real (or mocked) SQLite database
3. Mock Socket.IO
4. Mock email/webhook services
5. Mock LDAP

Result: Tests are slow, brittle, and test too many things at once.

#### 4. Difficult to Extend
- Adding a new role requires changes in 5+ places (auth decorator, permission matrix, multiple routes)
- Adding a new event sink (Slack webhook) requires modifying the existing Teams webhook code
- Changing from SQLite to PostgreSQL would require querying all 40+ routes

#### 5. Lack of Type Safety
No type hints means:
- IDE autocomplete doesn't work
- Static analysis tools can't catch bugs
- Future developers/agents must read implementation to understand APIs

### Requirements from CLAUDE.md

Key architectural principles that should guide this refactoring:

1. **Segregación de datos por empresa (CRÍTICO):** Toda query filtra por `company_id` del usuario autenticado
2. **Revocación de token JWT en <1 segundo:** Implementar blacklist con lookup <5ms
3. **Propagación en tiempo real <3 segundos:** WebSocket con salas segregadas por `company_id`
4. **Bloqueo optimista:** Versioning de tickets para evitar sobrescrituras concurrentes
5. **Auditoría completa:** Toda acción registrada con usuario, IP, timestamp, company_id
6. **Rate limiting:** 120 req/min por IP (RNF-03-07)
7. **8,000 empleados, 100 técnicos:** Soportar 100+ usuarios concurrentes

---

## Decision

Refactor TicketDesk to **Clean Architecture** (also called Hexagonal or Ports-and-Adapters):

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  (Flask routes, blueprints, HTTP handling, serializers)      │
└─────────────────────────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────────────────────────┐
│                  APPLICATION LAYER                           │
│  (Use cases, DTOs, service orchestration, business logic)    │
└─────────────────────────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────────────────────────┐
│              DOMAIN LAYER (Core business rules)              │
│  (Entities, value objects, domain exceptions, no frameworks) │
└─────────────────────────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                        │
│  (Database, email, webhooks, auth, cache, monitoring)       │
│  Implements abstract ports from Application/Domain           │
└─────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Dependency Inversion:** Core business logic depends on abstractions (ports), not concrete implementations
2. **Separation of Concerns:** Each layer has a single responsibility
3. **Testability:** Business logic testable without Flask, database, or external services
4. **Extensibility:** Add new adapters (e.g., Slack) without changing core logic
5. **Type Safety:** 100% type hints for IDE support and static analysis

### Implementation Strategy

**Phase-based refactoring (8 weeks, non-breaking):**

1. **Phase 1 (Week 1):** Create directory structure, don't change functionality
2. **Phase 2 (Weeks 2-3):** Extract domain models and repositories
3. **Phase 3 (Weeks 3-4):** Implement services with injected dependencies
4. **Phase 4 (Week 4+):** Convert routes to blueprints using services
5. **Phase 5 (Week 5):** Abstract infrastructure (auth, email, webhooks)
6. **Phase 6 (Week 6):** Refactor WebSocket with proper room management
7. **Phase 7 (Weeks 7-8):** Testing, documentation, optimization

### New Directory Structure

```
ticketdesk/
├── domain/              # Core business rules (no frameworks)
│   ├── entities.py      # Dataclasses: Ticket, User, Company
│   ├── enums.py         # TicketStatus, Priority, UserRole, etc.
│   ├── exceptions.py    # Domain-specific exceptions
│   └── value_objects.py # Email, TicketNumber, etc.
│
├── application/         # Use cases and orchestration
│   ├── dto.py           # CreateTicketDTO, UpdateTicketDTO, etc.
│   ├── services/        # TicketService, UserService, SLAService, etc.
│   └── ports/           # Abstract interfaces (TicketRepository, EmailGateway, etc.)
│
├── infrastructure/      # Concrete implementations
│   ├── database/        # SQLAlchemy models, repositories
│   ├── auth/            # JWT, LDAP, password hashing
│   ├── email/           # SMTP gateway
│   ├── webhooks/        # Teams, Slack (future)
│   ├── cache/           # Redis (optional, for JWT blacklist)
│   └── monitoring/      # Backup, watchdog, server monitor
│
└── presentation/        # HTTP/WebSocket layer
    ├── app.py           # Flask app factory
    ├── blueprints/      # auth, employee, technician, admin, api, health
    ├── middlewares/     # Auth, rate limit, error handling
    ├── websocket/       # Socket.IO handlers
    └── serializers/     # JSON serialization
```

---

## Alternatives Considered

### Alternative 1: Minimal Refactoring (Extract Routes to Blueprints Only)
**Approach:** Keep app.py mostly as-is, move routes to blueprints.

**Pros:**
- Faster implementation (2 weeks)
- Less code reorganization

**Cons:**
- Doesn't solve code duplication
- Still tightly coupled
- Testing remains difficult
- No enforced separation of concerns

**Rejected:** Doesn't address root causes.

### Alternative 2: Complete Rewrite to FastAPI/Next.js
**Approach:** Start over with a modern async framework.

**Pros:**
- Modern, async-native
- Could use TypeScript for type safety
- Fresh start without legacy baggage

**Cons:**
- **Much higher risk** (could introduce new bugs)
- Requires rewriting all business logic
- Staff needs to learn new stack
- Deployments must cutover entirely (no gradual migration)
- **3-4 months** vs 8 weeks
- Existing LDAP/webhook integrations must be re-verified

**Rejected:** Too risky for production system with 8,000 users.

### Alternative 3: Microservices Decomposition
**Approach:** Split into tickets service, auth service, notification service, etc.

**Pros:**
- Allows independent scaling
- Clear service boundaries
- Could use different tech per service

**Cons:**
- **Overengineering** for current scale (100 concurrent users on single server)
- Increases operational complexity (multiple DBs, service discovery, circuit breakers)
- Introduces distributed system problems (CAP theorem, eventual consistency)
- Network overhead

**Rejected:** Premature optimization. Clean Architecture within a monolith is right fit for current scale.

---

## Consequences

### Positive
1. **Testability:** Services tested without database/Flask (unit tests in <1s)
2. **Maintainability:** Adding a feature touches only 1-2 files, not scattered across 40+
3. **Type Safety:** IDE autocomplete, static analysis, fewer runtime bugs
4. **Extensibility:** Add Slack webhook without modifying Teams code
5. **Onboarding:** New developers/agents understand architecture faster
6. **Compliance:** Easier to audit (clear audit trail, explicit company segregation)

### Negative
1. **Initial Effort:** ~8 weeks of refactoring
2. **Code Growth:** ~7,800 lines of code (structured) vs 1,632 (monolithic)
3. **Learning Curve:** Team needs to understand ports/adapters pattern
4. **Risk of Regression:** Must test thoroughly during migration

### Mitigation
- Phases 1-2 have minimal risk (structural changes only)
- Phase 4 introduces tests incrementally
- E2E tests prevent regressions
- Backwards compatibility maintained (app.py migrated to new structure, not deleted)

---

## Implementation Notes

### Phase 1: Setup (Low Risk)
1. Create directory structure
2. Move models to `domain/entities.py`
3. Create port interfaces in `application/ports/`
4. No breaking changes yet

### Phase 2: Repositories (Medium Risk)
1. Create repository implementations
2. Gradually replace inline queries with repository calls
3. Old app.py queries deprecated but still work

### Phase 3: Services (Medium Risk)
1. Extract business logic from routes to services
2. Services use repositories (not direct DB access)
3. Services have 100% type hints

### Phase 4: Blueprints (Medium Risk)
1. Routes become thin adapters (deserialize → call service → serialize)
2. Auth/validation in decorators
3. Error handling centralized

### Phase 5+: Infrastructure (Low Risk)
1. Auth/email/webhooks already abstracted in ports
2. Easy to swap implementations

---

## Acceptance Criteria

- [ ] All 40+ routes refactored to blueprints
- [ ] All business logic in services (routes ≤30 lines)
- [ ] 100% type hints in domain, application, infrastructure layers
- [ ] >80% test coverage for services and repositories
- [ ] Zero change in API behavior (external clients see no difference)
- [ ] Company segregation enforced in every service method
- [ ] JWT blacklist lookup <5ms (benchmarked)
- [ ] Performance equivalent to current app.py (API response times, throughput)
- [ ] Full audit trail maintained (no regression)
- [ ] Documentation: architecture guide, service APIs, testing guide

---

## Related Decisions

- **ADR-002** (Future): Database migration strategy (SQLite → PostgreSQL path)
- **ADR-003** (Future): Caching strategy for JWT blacklist (in-memory vs Redis)
- **ADR-004** (Future): Event bus for real-time updates (current: direct Socket.IO calls)

---

## References

- CLAUDE.md (project requirements and design principles)
- ARCHITECTURE_ANALYSIS.md (detailed problem analysis and refactoring plan)
- Clean Code by Robert Martin
- Hexagonal Architecture by Alistair Cockburn
- The Clean Architecture blog series
