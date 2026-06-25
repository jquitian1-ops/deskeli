-- ═════════════════════════════════════════════════════════════════════════════
-- TICKETDESK ENTERPRISE v2.1 - BD OPTIMIZATION COMPLETA
-- ═════════════════════════════════════════════════════════════════════════════
-- PASO 1: WAL MODE + PRAGMAS
-- PASO 2: 20 ÍNDICES CRÍTICOS
-- PASO 3: FULL TEXT SEARCH (FTS5)
-- PASO 4: AUTO-UPDATE TRIGGERS
-- ═════════════════════════════════════════════════════════════════════════════

-- ═════════════════════════════════════════════════════════════════════════════
-- SECCIÓN 1: PRAGMAS CRÍTICAS DE RENDIMIENTO
-- ═════════════════════════════════════════════════════════════════════════════

-- Habilitar WAL mode para lecturas + escrituras concurrentes
PRAGMA journal_mode = WAL;

-- Aumentar cache a 64MB (-64000 = 64MB con page_size=1000)
PRAGMA cache_size = -64000;

-- Timeout 30 segundos para operaciones de BD
PRAGMA busy_timeout = 30000;

-- Synchronous mode 1 = NORMAL (fuerza SYNC en transacciones, no en cada query)
PRAGMA synchronous = 1;

-- Auto-vacuum incremental (limpia espacio cada 1000 cambios)
PRAGMA auto_vacuum = 2;
PRAGMA incremental_vacuum(1000);

-- Mmap para lecturas rápidas (256MB mapping)
PRAGMA mmap_size = 268435456;

-- Foreign keys
PRAGMA foreign_keys = ON;

-- Temp_store en RAM
PRAGMA temp_store = MEMORY;

-- ═════════════════════════════════════════════════════════════════════════════
-- SECCIÓN 2: ÍNDICES CRÍTICOS (20 ÍNDICES)
-- ═════════════════════════════════════════════════════════════════════════════

-- ÍNDICE 1-3: TABLA TICKETS (company_id + status + deadline)
CREATE INDEX IF NOT EXISTS idx_tickets_company_status
  ON tickets(company_id, status);

CREATE INDEX IF NOT EXISTS idx_tickets_company_sla_deadline
  ON tickets(company_id, sla_deadline);

CREATE INDEX IF NOT EXISTS idx_tickets_assignee_company
  ON tickets(assignee_id, company_id, status);

-- ÍNDICE 4-6: BÚSQUEDA RÁPIDA DE TICKETS
CREATE INDEX IF NOT EXISTS idx_tickets_created_at
  ON tickets(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tickets_updated_at
  ON tickets(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_tickets_company_created
  ON tickets(company_id, created_at DESC);

-- ÍNDICE 7-8: TABLA USERS
CREATE INDEX IF NOT EXISTS idx_users_company_username
  ON users(company_id, username);

CREATE INDEX IF NOT EXISTS idx_users_company_role
  ON users(company_id, role);

-- ÍNDICE 9: TOKEN BLACKLIST (CRÍTICO PARA REVOCACIÓN JWT)
CREATE INDEX IF NOT EXISTS idx_token_blacklist_jti_expires
  ON token_blacklist(jti, expires_at);

-- ÍNDICE 10: BÚSQUEDA RÁPIDA EN BLACKLIST POR EXPIRACIÓN
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires
  ON token_blacklist(expires_at);

-- ÍNDICE 11-12: AUDIT LOG
CREATE INDEX IF NOT EXISTS idx_audit_log_user_company
  ON audit_log(user_id, company_id);

CREATE INDEX IF NOT EXISTS idx_audit_log_created_company
  ON audit_log(created_at DESC, company_id);

-- ÍNDICE 13: COMMENTS
CREATE INDEX IF NOT EXISTS idx_comments_ticket_company
  ON comments(ticket_id, company_id, created_at DESC);

-- ÍNDICE 14: SLA ESCALATIONS
CREATE INDEX IF NOT EXISTS idx_sla_escalations_ticket
  ON sla_escalations(ticket_id, escalation_level);

-- ÍNDICE 15: TECHNICIAN ASSIGNMENTS
CREATE INDEX IF NOT EXISTS idx_assignments_technician_status
  ON technician_assignments(technician_id, status);

-- ÍNDICE 16: TEMPLATES
CREATE INDEX IF NOT EXISTS idx_templates_company_active
  ON templates(company_id, is_active);

-- ÍNDICE 17: CONFIG
CREATE INDEX IF NOT EXISTS idx_config_company_key
  ON config(company_id, config_key);

-- ÍNDICE 18: NOTIFICATIONS
CREATE INDEX IF NOT EXISTS idx_notifications_user_company
  ON notifications(user_id, company_id, read_at);

-- ÍNDICE 19: WEBHOOK DELIVERIES
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_event_status
  ON webhook_deliveries(event_type, delivery_status);

-- ÍNDICE 20: SYSTEM LOGS (AUDITORÍA)
CREATE INDEX IF NOT EXISTS idx_system_log_level_source
  ON system_log(level, source, created_at DESC);

-- ═════════════════════════════════════════════════════════════════════════════
-- SECCIÓN 3: FULL TEXT SEARCH (FTS5)
-- ═════════════════════════════════════════════════════════════════════════════

-- Crear tabla FTS5 virtual para búsqueda de texto completo
CREATE VIRTUAL TABLE IF NOT EXISTS tickets_fts
USING fts5(
  ticket_id UNINDEXED,
  company_id UNINDEXED,
  title,
  description,
  tags,
  content='tickets',
  content_rowid='id'
);

-- Poplar tabla FTS5 con tickets existentes
INSERT OR IGNORE INTO tickets_fts(rowid, ticket_id, company_id, title, description, tags)
SELECT id, id, company_id, title, description, tags FROM tickets;

-- Crear tabla FTS5 virtual para comentarios
CREATE VIRTUAL TABLE IF NOT EXISTS comments_fts
USING fts5(
  comment_id UNINDEXED,
  ticket_id UNINDEXED,
  company_id UNINDEXED,
  content,
  content='comments',
  content_rowid='id'
);

-- Popular tabla FTS5 de comentarios
INSERT OR IGNORE INTO comments_fts(rowid, comment_id, ticket_id, company_id, content)
SELECT id, id, ticket_id, (SELECT company_id FROM tickets WHERE tickets.id = comments.ticket_id), content
FROM comments;

-- ═════════════════════════════════════════════════════════════════════════════
-- SECCIÓN 4: TRIGGERS PARA AUTO-UPDATE TIMESTAMPS
-- ═════════════════════════════════════════════════════════════════════════════

-- Trigger: actualizar updated_at en tickets
CREATE TRIGGER IF NOT EXISTS trg_tickets_update_timestamp
AFTER UPDATE ON tickets
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
  UPDATE tickets SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger: actualizar FTS5 cuando se modifica un ticket
CREATE TRIGGER IF NOT EXISTS trg_tickets_fts_update
AFTER UPDATE ON tickets
FOR EACH ROW
BEGIN
  INSERT INTO tickets_fts(tickets_fts, rowid, ticket_id, company_id, title, description, tags)
  VALUES('delete', NEW.id, NEW.id, NEW.company_id, NEW.title, NEW.description, NEW.tags);
  INSERT INTO tickets_fts(rowid, ticket_id, company_id, title, description, tags)
  VALUES(NEW.id, NEW.id, NEW.company_id, NEW.title, NEW.description, NEW.tags);
END;

-- Trigger: insertar en FTS5 cuando se crea un ticket
CREATE TRIGGER IF NOT EXISTS trg_tickets_fts_insert
AFTER INSERT ON tickets
FOR EACH ROW
BEGIN
  INSERT INTO tickets_fts(rowid, ticket_id, company_id, title, description, tags)
  VALUES(NEW.id, NEW.id, NEW.company_id, NEW.title, NEW.description, NEW.tags);
END;

-- Trigger: actualizar FTS5 cuando se modifica un comentario
CREATE TRIGGER IF NOT EXISTS trg_comments_fts_update
AFTER UPDATE ON comments
FOR EACH ROW
BEGIN
  INSERT INTO comments_fts(comments_fts, rowid, comment_id, ticket_id, company_id, content)
  VALUES('delete', NEW.id, NEW.id, NEW.ticket_id, (SELECT company_id FROM tickets WHERE id = NEW.ticket_id), NEW.content);
  INSERT INTO comments_fts(rowid, comment_id, ticket_id, company_id, content)
  VALUES(NEW.id, NEW.id, NEW.ticket_id, (SELECT company_id FROM tickets WHERE id = NEW.ticket_id), NEW.content);
END;

-- Trigger: insertar en FTS5 cuando se crea un comentario
CREATE TRIGGER IF NOT EXISTS trg_comments_fts_insert
AFTER INSERT ON comments
FOR EACH ROW
BEGIN
  INSERT INTO comments_fts(rowid, comment_id, ticket_id, company_id, content)
  VALUES(NEW.id, NEW.id, NEW.ticket_id, (SELECT company_id FROM tickets WHERE id = NEW.ticket_id), NEW.content);
END;

-- Trigger: auto-update created_at en usuarios
CREATE TRIGGER IF NOT EXISTS trg_users_created_at
AFTER INSERT ON users
FOR EACH ROW
WHEN NEW.created_at IS NULL
BEGIN
  UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger: auto-update updated_at en comentarios
CREATE TRIGGER IF NOT EXISTS trg_comments_update_timestamp
AFTER UPDATE ON comments
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
  UPDATE comments SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ═════════════════════════════════════════════════════════════════════════════
-- SECCIÓN 5: VERIFICACIÓN & ANÁLISIS
-- ═════════════════════════════════════════════════════════════════════════════

-- Verificar WAL mode está activo
PRAGMA journal_mode;

-- Ver todos los índices creados
SELECT name, tbl_name, sql FROM sqlite_master
WHERE type='index' AND name LIKE 'idx_%'
ORDER BY tbl_name;

-- Ver estadísticas de las tablas principales
SELECT
  name,
  (SELECT COUNT(*) FROM tickets WHERE company_id = t.company_id) as ticket_count,
  (SELECT COUNT(*) FROM users WHERE company_id = t.company_id) as user_count
FROM (SELECT DISTINCT company_id FROM tickets) t;

-- Verificar FTS5 está disponible
PRAGMA compile_options LIKE 'ENABLE_FTS5';
