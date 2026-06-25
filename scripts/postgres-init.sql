-- TicketDesk Database Initialization Script
-- PostgreSQL 15+ compatible

-- ========================================================================
-- 1. Extensions
-- ========================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Para búsqueda full-text
CREATE EXTENSION IF NOT EXISTS "unaccent";  -- Para búsqueda sin acentos

-- ========================================================================
-- 2. ENUMS & TYPES
-- ========================================================================
CREATE TYPE ticket_status AS ENUM (
  'open',
  'in_progress',
  'waiting_customer',
  'escalated',
  'resolved',
  'closed'
);

CREATE TYPE ticket_priority AS ENUM (
  'low',
  'medium',
  'high',
  'critical'
);

CREATE TYPE ticket_category AS ENUM (
  'infrastructure',
  'software',
  'hardware',
  'network',
  'database',
  'security',
  'other'
);

CREATE TYPE user_role AS ENUM (
  'admin',
  'technician',
  'employee'
);

CREATE TYPE audit_action AS ENUM (
  'login',
  'logout',
  'create',
  'update',
  'delete',
  'escalate',
  'export',
  'config_change',
  'session_timeout',
  'auth_failed'
);

-- ========================================================================
-- 3. Tables - Companies
-- ========================================================================
CREATE TABLE IF NOT EXISTS companies (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name VARCHAR(255) NOT NULL UNIQUE,
  description TEXT,
  icon_url VARCHAR(255),
  color_code VARCHAR(7),
  ldap_base_dn VARCHAR(255),
  ldap_server VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_companies_name ON companies(name);

-- ========================================================================
-- 4. Tables - Users
-- ========================================================================
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  username VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  full_name VARCHAR(255),
  role user_role NOT NULL DEFAULT 'employee',
  password_hash VARCHAR(255),
  is_active BOOLEAN DEFAULT true,
  is_ldap_user BOOLEAN DEFAULT true,
  last_login TIMESTAMP,
  session_timeout_minutes INT DEFAULT 15,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(company_id, username),
  UNIQUE(company_id, email)
);

CREATE INDEX idx_users_company ON users(company_id);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_email ON users(email);

-- ========================================================================
-- 5. Tables - JWT Token Blacklist
-- ========================================================================
CREATE TABLE IF NOT EXISTS token_blacklist (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  jti VARCHAR(255) NOT NULL UNIQUE,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_token_blacklist_expires ON token_blacklist(expires_at);
CREATE INDEX idx_token_blacklist_jti ON token_blacklist(jti);

-- ========================================================================
-- 6. Tables - Tickets
-- ========================================================================
CREATE TABLE IF NOT EXISTS tickets (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  ticket_number VARCHAR(50) NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  category ticket_category DEFAULT 'other',
  priority ticket_priority DEFAULT 'medium',
  status ticket_status DEFAULT 'open',

  created_by UUID NOT NULL REFERENCES users(id),
  assigned_to UUID REFERENCES users(id),

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  resolved_at TIMESTAMP,
  closed_at TIMESTAMP,

  version INT DEFAULT 1,  -- Optimistic locking
  affected_system VARCHAR(255),

  UNIQUE(company_id, ticket_number)
);

CREATE INDEX idx_tickets_company ON tickets(company_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_assigned_to ON tickets(assigned_to);
CREATE INDEX idx_tickets_created_by ON tickets(created_by);
CREATE INDEX idx_tickets_created_at ON tickets(created_at DESC);
CREATE INDEX idx_tickets_updated_at ON tickets(updated_at DESC);

-- Full-text search index
CREATE INDEX idx_tickets_fts ON tickets USING gin(
  to_tsvector('spanish', title || ' ' || COALESCE(description, ''))
);

-- ========================================================================
-- 7. Tables - Ticket Comments
-- ========================================================================
CREATE TABLE IF NOT EXISTS ticket_comments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id),
  comment TEXT NOT NULL,
  is_internal BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_comments_ticket ON ticket_comments(ticket_id);
CREATE INDEX idx_comments_user ON ticket_comments(user_id);
CREATE INDEX idx_comments_created_at ON ticket_comments(created_at DESC);

-- Full-text search
CREATE INDEX idx_comments_fts ON ticket_comments USING gin(
  to_tsvector('spanish', comment)
);

-- ========================================================================
-- 8. Tables - SLA (Service Level Agreements)
-- ========================================================================
CREATE TABLE IF NOT EXISTS sla_rules (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  priority ticket_priority NOT NULL,
  response_time_minutes INT NOT NULL,
  resolution_time_minutes INT NOT NULL,
  escalation_threshold_percent INT DEFAULT 50,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(company_id, priority)
);

CREATE INDEX idx_sla_rules_company ON sla_rules(company_id);

CREATE TABLE IF NOT EXISTS ticket_sla (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  ticket_id UUID NOT NULL UNIQUE REFERENCES tickets(id) ON DELETE CASCADE,
  sla_rule_id UUID NOT NULL REFERENCES sla_rules(id),
  response_due_at TIMESTAMP NOT NULL,
  resolution_due_at TIMESTAMP NOT NULL,
  response_breach_at TIMESTAMP,
  resolution_breach_at TIMESTAMP,
  escalation_level INT DEFAULT 0,
  escalated_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ticket_sla_ticket ON ticket_sla(ticket_id);
CREATE INDEX idx_ticket_sla_due_dates ON ticket_sla(response_due_at, resolution_due_at);

-- ========================================================================
-- 9. Tables - Audit Log
-- ========================================================================
CREATE TABLE IF NOT EXISTS system_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  action audit_action NOT NULL,
  resource_type VARCHAR(50),
  resource_id VARCHAR(100),
  description TEXT,
  ip_address INET,
  user_agent TEXT,
  old_values JSONB,
  new_values JSONB,
  success BOOLEAN DEFAULT true,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_log_company ON system_log(company_id);
CREATE INDEX idx_system_log_user ON system_log(user_id);
CREATE INDEX idx_system_log_action ON system_log(action);
CREATE INDEX idx_system_log_created_at ON system_log(created_at DESC);
CREATE INDEX idx_system_log_resource ON system_log(resource_type, resource_id);

-- ========================================================================
-- 10. Tables - Configuration (Admin Settings)
-- ========================================================================
CREATE TABLE IF NOT EXISTS config_settings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  key VARCHAR(100) NOT NULL,
  value TEXT,
  value_type VARCHAR(50),  -- 'string', 'integer', 'boolean', 'json'
  description TEXT,
  updated_by UUID REFERENCES users(id),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(company_id, key)
);

CREATE INDEX idx_config_settings_company ON config_settings(company_id);
CREATE INDEX idx_config_settings_key ON config_settings(key);

-- ========================================================================
-- 11. Tables - Technician Profiles (Skills & Load)
-- ========================================================================
CREATE TABLE IF NOT EXISTS technician_profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  specialization VARCHAR(100),
  max_concurrent_tickets INT DEFAULT 10,
  is_available BOOLEAN DEFAULT true,
  expertise_tags TEXT[],  -- Array de expertise areas
  availability_schedule JSONB,  -- Horarios de disponibilidad
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_technician_profiles_user ON technician_profiles(user_id);
CREATE INDEX idx_technician_profiles_available ON technician_profiles(is_available);

-- ========================================================================
-- 12. Tables - Webhooks (Teams Integration)
-- ========================================================================
CREATE TABLE IF NOT EXISTS webhooks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  url VARCHAR(2048) NOT NULL,
  event_type VARCHAR(50),  -- 'ticket_created', 'ticket_updated', 'sla_escalated'
  is_active BOOLEAN DEFAULT true,
  headers JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(company_id, name)
);

CREATE INDEX idx_webhooks_company ON webhooks(company_id);
CREATE INDEX idx_webhooks_active ON webhooks(is_active);

-- ========================================================================
-- 13. Tables - Knowledge Base (para Bot IA)
-- ========================================================================
CREATE TABLE IF NOT EXISTS knowledge_base (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  category VARCHAR(100),
  tags TEXT[],
  embedding VECTOR(1536),  -- Para búsqueda semántica (requiere pgvector)
  helpful_count INT DEFAULT 0,
  not_helpful_count INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_kb_company ON knowledge_base(company_id);
CREATE INDEX idx_kb_category ON knowledge_base(category);

-- ========================================================================
-- 14. Tables - Server Health Monitoring
-- ========================================================================
CREATE TABLE IF NOT EXISTS monitored_servers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  server_name VARCHAR(255) NOT NULL,
  ip_address INET NOT NULL,
  port INT,
  check_interval_seconds INT DEFAULT 300,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(company_id, server_name)
);

CREATE TABLE IF NOT EXISTS server_health_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  server_id UUID NOT NULL REFERENCES monitored_servers(id) ON DELETE CASCADE,
  status VARCHAR(50),  -- 'healthy', 'unhealthy', 'timeout'
  response_time_ms INT,
  error_message TEXT,
  checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_server_health_server ON server_health_logs(server_id);
CREATE INDEX idx_server_health_checked_at ON server_health_logs(checked_at DESC);

-- ========================================================================
-- 15. Functions & Triggers
-- ========================================================================

-- Función para actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para users
CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Trigger para tickets
CREATE TRIGGER update_tickets_updated_at
BEFORE UPDATE ON tickets
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Trigger para comments
CREATE TRIGGER update_ticket_comments_updated_at
BEFORE UPDATE ON ticket_comments
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Trigger para technician_profiles
CREATE TRIGGER update_technician_profiles_updated_at
BEFORE UPDATE ON technician_profiles
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Función para auto-incrementar ticket_number
CREATE OR REPLACE FUNCTION generate_ticket_number()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.ticket_number IS NULL THEN
    NEW.ticket_number := 'TKT-' || to_char(CURRENT_TIMESTAMP, 'YYYYMMDD') || '-' ||
                         LPAD(CAST(NEXTVAL('ticket_number_seq_' || NEW.company_id) AS TEXT), 6, '0');
  END IF;
  RETURN NEW;
END;
$$ language 'plpgsql';

-- ========================================================================
-- 16. Initial Data
-- ========================================================================

-- Insertar empresas de prueba
INSERT INTO companies (id, name, description, color_code)
VALUES
  ('550e8400-e29b-41d4-a716-446655440000', 'Manufacturas Eliot', 'Primera empresa de manufactura', '#FF6B6B'),
  ('550e8400-e29b-41d4-a716-446655440001', 'Pash', 'Segunda empresa', '#4ECDC4'),
  ('550e8400-e29b-41d4-a716-446655440002', 'Primatela', 'Tercera empresa', '#45B7D1')
ON CONFLICT DO NOTHING;

-- Insertar usuarios de prueba
INSERT INTO users (id, company_id, username, email, full_name, role, password_hash, is_ldap_user)
VALUES
  ('650e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440000', 'admin_eliot', 'admin@eliot.local', 'Admin Eliot', 'admin', 'pbkdf2:sha256:600000$...', false),
  ('650e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', 'tech_eliot', 'tech@eliot.local', 'Técnico Eliot', 'technician', 'pbkdf2:sha256:600000$...', false),
  ('650e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', 'emp_eliot', 'emp@eliot.local', 'Empleado Eliot', 'employee', 'pbkdf2:sha256:600000$...', false)
ON CONFLICT DO NOTHING;

-- Insertar reglas SLA por defecto
INSERT INTO sla_rules (company_id, priority, response_time_minutes, resolution_time_minutes, escalation_threshold_percent)
SELECT id, priority, response_time, resolution_time, 50
FROM (
  SELECT '550e8400-e29b-41d4-a716-446655440000' as id, 'critical'::ticket_priority as priority, 30 as response_time, 120 as resolution_time
  UNION ALL
  SELECT '550e8400-e29b-41d4-a716-446655440000', 'high'::ticket_priority, 60, 240
  UNION ALL
  SELECT '550e8400-e29b-41d4-a716-446655440000', 'medium'::ticket_priority, 120, 480
  UNION ALL
  SELECT '550e8400-e29b-41d4-a716-446655440000', 'low'::ticket_priority, 240, 1440
) AS sla
ON CONFLICT DO NOTHING;

-- ========================================================================
-- 17. Views para Analytics
-- ========================================================================

CREATE OR REPLACE VIEW v_ticket_metrics AS
SELECT
  t.company_id,
  COUNT(*) as total_tickets,
  COUNT(CASE WHEN t.status = 'open' THEN 1 END) as open_tickets,
  COUNT(CASE WHEN t.status = 'in_progress' THEN 1 END) as in_progress_tickets,
  COUNT(CASE WHEN t.status = 'resolved' THEN 1 END) as resolved_tickets,
  COUNT(CASE WHEN t.status = 'closed' THEN 1 END) as closed_tickets,
  AVG(EXTRACT(EPOCH FROM (COALESCE(t.closed_at, CURRENT_TIMESTAMP) - t.created_at)) / 3600) as avg_resolution_hours
FROM tickets t
GROUP BY t.company_id;

-- ========================================================================
-- 18. Grants & Security
-- ========================================================================

-- Crear rol de aplicación (opcional)
-- DO $$
-- BEGIN
--   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ticketdesk_app') THEN
--     CREATE ROLE ticketdesk_app;
--   END IF;
-- END$$;

-- GRANT CONNECT ON DATABASE ticketdesk TO ticketdesk_app;
-- GRANT USAGE ON SCHEMA public TO ticketdesk_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ticketdesk_app;

-- ========================================================================
-- Done!
-- ========================================================================
SELECT 'TicketDesk Database initialized successfully!' as message;
