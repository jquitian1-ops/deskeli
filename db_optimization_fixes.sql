-- ════════════════════════════════════════════════════════════════════════════
-- TICKETDESK ENTERPRISE - DATABASE OPTIMIZATION FIXES
-- Ejecutar en orden. Cada sección es idempotente.
-- ════════════════════════════════════════════════════════════════════════════

-- ════════════════════════════════════════════════════════════════════════════
-- FASE 1: WAL MODE + PRAGMAS DE PERFORMANCE
-- ════════════════════════════════════════════════════════════════════════════

-- ACTIVAR WAL MODE (Critical para concurrencia)
PRAGMA journal_mode = WAL;

-- WAL auto-checkpoint cada 1000 frames (recomendado)
PRAGMA wal_autocheckpoint = 1000;

-- Cambiar synchronous a NORMAL (con WAL es seguro)
PRAGMA synchronous = NORMAL;

-- Aumentar cache a 20MB (de 2MB)
PRAGMA cache_size = -20000;

-- Aumentar busy timeout a 30 segundos
PRAGMA busy_timeout = 30000;

-- Aumentar temp_store para queries complejas
PRAGMA temp_store = MEMORY;

-- ════════════════════════════════════════════════════════════════════════════
-- FASE 2: ÍNDICES CRÍTICOS
-- ════════════════════════════════════════════════════════════════════════════

-- ─ TABLA: tickets (La más crítica)
-- Índice para filtro: company + status (dashboard admin, técnicos)
CREATE INDEX IF NOT EXISTS idx_tickets_company_status
ON tickets(company, status);

-- Índice para SLA deadline (alertas, escalaciones)
CREATE INDEX IF NOT EXISTS idx_tickets_sla_deadline
ON tickets(sla_deadline, company);

-- Índice para cola de asignado (dashboard técnico)
CREATE INDEX IF NOT EXISTS idx_tickets_assignee
ON tickets(assignee_id, status);

-- Índice para tickets del creador (dashboard empleado)
CREATE INDEX IF NOT EXISTS idx_tickets_creator
ON tickets(creator_id, status);

-- Índice para búsqueda por prioridad + empresa
CREATE INDEX IF NOT EXISTS idx_tickets_priority
ON tickets(priority, company);

-- Índice para búsqueda ticket_number (lookup único)
CREATE INDEX IF NOT EXISTS idx_tickets_number
ON tickets(ticket_number);

-- Índice para resolved_at (reports de tiempo medio resolución)
CREATE INDEX IF NOT EXISTS idx_tickets_resolved_at
ON tickets(resolved_at, company);

-- ─ TABLA: token_blacklist (CRÍTICO: Lookup JTI <5ms)
CREATE INDEX IF NOT EXISTS idx_blacklist_jti
ON token_blacklist(jti);

-- Índice para purga automática (expiradas)
CREATE INDEX IF NOT EXISTS idx_blacklist_expires
ON token_blacklist(expires_at);

-- ─ TABLA: audit_logs (Compliance RNF-01-01)
CREATE INDEX IF NOT EXISTS idx_audit_user_date
ON audit_logs(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_entity
ON audit_logs(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_audit_action_date
ON audit_logs(action, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_created_at
ON audit_logs(created_at DESC);

-- ─ TABLA: messages (Chat en tiempo real)
CREATE INDEX IF NOT EXISTS idx_messages_ticket
ON messages(ticket_id, created_at);

CREATE INDEX IF NOT EXISTS idx_messages_user
ON messages(user_id, created_at);

-- ─ TABLA: user_sessions (Control de sesiones)
CREATE INDEX IF NOT EXISTS idx_sessions_user
ON user_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_sessions_token
ON user_sessions(session_token);

-- ─ TABLA: servers (Monitoreo)
CREATE INDEX IF NOT EXISTS idx_servers_company
ON servers(company, is_online);

CREATE INDEX IF NOT EXISTS idx_servers_ping
ON servers(last_ping);

-- ─ TABLA: webhooks
CREATE INDEX IF NOT EXISTS idx_webhooks_company
ON webhooks(company, is_active);

-- ─ TABLA: templates
CREATE INDEX IF NOT EXISTS idx_templates_company
ON templates(company, is_system);

-- ─ TABLA: bot_knowledge
CREATE INDEX IF NOT EXISTS idx_botknowledge_category
ON bot_knowledge(category);

-- ════════════════════════════════════════════════════════════════════════════
-- FASE 3: FULL TEXT SEARCH (FTS5)
-- ════════════════════════════════════════════════════════════════════════════

-- Crear tabla virtual FTS5 para búsqueda rápida
CREATE VIRTUAL TABLE IF NOT EXISTS tickets_fts USING fts5(
    ticket_number UNINDEXED,
    title,
    description,
    category,
    content=tickets,
    content_rowid=id
);

-- Insertar datos existentes en FTS5
-- (Ejecutar solo si tabla FTS5 está vacía)
INSERT OR IGNORE INTO tickets_fts(rowid, ticket_number, title, description, category)
SELECT id, ticket_number, title, description, category FROM tickets;

-- Triggers para mantener FTS5 sincronizado con tickets

-- Trigger: INSERT en tickets
DROP TRIGGER IF EXISTS tickets_ai;
CREATE TRIGGER tickets_ai AFTER INSERT ON tickets BEGIN
  INSERT INTO tickets_fts(rowid, ticket_number, title, description, category)
  VALUES (new.id, new.ticket_number, new.title, new.description, new.category);
END;

-- Trigger: DELETE en tickets
DROP TRIGGER IF EXISTS tickets_ad;
CREATE TRIGGER tickets_ad AFTER DELETE ON tickets BEGIN
  INSERT INTO tickets_fts(tickets_fts, rowid, ticket_number, title, description, category)
  VALUES('delete', old.id, old.ticket_number, old.title, old.description, old.category);
END;

-- Trigger: UPDATE en tickets
DROP TRIGGER IF EXISTS tickets_au;
CREATE TRIGGER tickets_au AFTER UPDATE ON tickets BEGIN
  INSERT INTO tickets_fts(tickets_fts, rowid, ticket_number, title, description, category)
  VALUES('delete', old.id, old.ticket_number, old.title, old.description, old.category);
  INSERT INTO tickets_fts(rowid, ticket_number, title, description, category)
  VALUES (new.id, new.ticket_number, new.title, new.description, new.category);
END;

-- ════════════════════════════════════════════════════════════════════════════
-- FASE 4: VACUUM Y ANALYZE (Optimización final)
-- ════════════════════════════════════════════════════════════════════════════

-- Reorganizar BD (eliminar espacio desperdiciado)
VACUUM;

-- Actualizar estadísticas para query planner
ANALYZE;

-- ════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN POST-OPTIMIZACIÓN
-- ════════════════════════════════════════════════════════════════════════════

-- Verificar que WAL está activado
.echo on
PRAGMA journal_mode;
-- Debe retornar: wal

-- Verificar pragmas de performance
PRAGMA synchronous;
-- Debe retornar: 1 (NORMAL)

PRAGMA cache_size;
-- Debe retornar: -20000

PRAGMA busy_timeout;
-- Debe retornar: 30000

-- Contar índices creados
SELECT COUNT(*) as total_indices FROM sqlite_master
WHERE type='index' AND sql IS NOT NULL;
-- Debe retornar: 20+ índices

-- Verificar FTS5 creado
SELECT COUNT(*) as fts5_tables FROM sqlite_master
WHERE type='table' AND name LIKE '%_fts%';
-- Debe retornar: 1

-- Ver estructura FTS5
PRAGMA table_info(tickets_fts);

-- ════════════════════════════════════════════════════════════════════════════
-- QUERIES PARA TESTING DE PERFORMANCE
-- ════════════════════════════════════════════════════════════════════════════

-- Test 1: Búsqueda FTS5 (debe ser <10ms)
-- EXPLAIN QUERY PLAN SELECT * FROM tickets_fts
-- WHERE tickets_fts MATCH 'wifi network';

-- Test 2: Cola de técnico (debe ser <100ms)
-- EXPLAIN QUERY PLAN SELECT * FROM tickets
-- WHERE company = 'eliot' AND status IN ('open', 'in_progress')
-- AND assignee_id = 2
-- ORDER BY sla_deadline
-- LIMIT 20;

-- Test 3: SLA escalado (debe ser <50ms)
-- EXPLAIN QUERY PLAN SELECT * FROM tickets
-- WHERE company = 'eliot'
-- AND sla_deadline < datetime('now')
-- LIMIT 10;

-- Test 4: Tokens blacklist lookup (debe ser <5ms)
-- EXPLAIN QUERY PLAN SELECT * FROM token_blacklist
-- WHERE jti = 'abc123def456';

-- Test 5: Audit trail (debe ser <100ms)
-- EXPLAIN QUERY PLAN SELECT * FROM audit_logs
-- WHERE user_id = 1
-- ORDER BY created_at DESC
-- LIMIT 50;

-- ════════════════════════════════════════════════════════════════════════════
-- MANTENIMIENTO AUTOMÁTICO
-- ════════════════════════════════════════════════════════════════════════════

-- Purgar tokens blacklist expirados (ejecutar cada hora)
-- DELETE FROM token_blacklist
-- WHERE expires_at < datetime('now');

-- Reorganizar FTS5 (ejecutar noche/fin de semana)
-- INSERT INTO tickets_fts(tickets_fts) VALUES('optimize');

-- VACUUM incremental (ejecutar diariamente)
-- PRAGMA incremental_vacuum(100000);

-- ════════════════════════════════════════════════════════════════════════════
