# TicketDesk Infrastructure Overview

Descripción completa de la arquitectura de infraestructura desplegada con Terraform.

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AWS Region (us-east-1)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                       VPC (10.0.0.0/16)                      │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │                                                                │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐   │  │
│  │  │   Public Net    │  │   Public Net    │  │  Internet  │   │  │
│  │  │  AZ-1 (10.0.1)  │  │  AZ-2 (10.0.2)  │  │  Gateway   │   │  │
│  │  └────────┬────────┘  └────────┬────────┘  └────────────┘   │  │
│  │           │                    │                 │           │  │
│  │  ┌────────▼────────────────────▼─────────────┐              │  │
│  │  │    Application Load Balancer (ALB)        │              │  │
│  │  │     Port 80 → 443 (HTTPS)                 │              │  │
│  │  │     Health Check: /api/health             │              │  │
│  │  └────────┬────────────────────┬─────────────┘              │  │
│  │           │                    │                            │  │
│  │  ┌────────▼────────────────────▼─────────────┐              │  │
│  │  │         VPC Endpoints                     │              │  │
│  │  │  • S3 (para backups)                      │              │  │
│  │  │  • CloudWatch Logs                        │              │  │
│  │  └──────────────────────────────────────────┘              │  │
│  │           │                    │                            │  │
│  │  ┌────────▼────────────────────▼─────────────┐              │  │
│  │  │       Private Subnets (App Layer)         │              │  │
│  │  │  AZ-1 (10.0.10.0/24)  AZ-2 (10.0.11.0/24) │              │  │
│  │  │                                            │              │  │
│  │  │  ┌──────────────┐  ┌──────────────┐      │              │  │
│  │  │  │ ECS Task 1   │  │ ECS Task 2   │      │              │  │
│  │  │  │ Flask App    │  │ Flask App    │      │              │  │
│  │  │  │ Port 5050    │  │ Port 5050    │      │              │  │
│  │  │  └──────┬───────┘  └──────┬───────┘      │              │  │
│  │  │         │                 │              │              │  │
│  │  └────────┬─────────────────┬────────────────┘              │  │
│  │           │                 │                              │  │
│  │  ┌────────▼──────┐  ┌───────▼──────────────┐              │  │
│  │  │   RDS Cluster  │  │  Redis Replication  │              │  │
│  │  │  (PostgreSQL)  │  │  Group (Sessions)   │              │  │
│  │  │   Multi-AZ     │  │  Multi-node Cluster │              │  │
│  │  │  Port 5432     │  │  Port 6379          │              │  │
│  │  └────────────────┘  └─────────────────────┘              │  │
│  │           │                 │                              │  │
│  │  ┌────────▼─────────────────▼─────────────┐              │  │
│  │  │      CloudWatch Logs & Monitoring      │              │  │
│  │  │  • ECS Logs: /ecs/app                  │              │  │
│  │  │  • RDS Enhanced Monitoring             │              │  │
│  │  │  • Application Insights                │              │  │
│  │  └────────────────────────────────────────┘              │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │            S3 Backup Bucket                              │   │
│  │  • Versioning enabled                                    │   │
│  │  • Encryption at rest (KMS)                             │   │
│  │  • Lifecycle: 30-day retention                          │   │
│  │  • CloudFront CDN (optional)                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

          │
          ▼
    ┌──────────────┐
    │  Route 53    │
    │  DNS Record  │
    └──────────────┘
```

## Componentes Principales

### 1. Networking (VPC Module)

**Objetivo:** Proporcionar aislamiento de red y conectividad.

```
VPC CIDR: 10.0.0.0/16

Subnets Públicas (ALB):
├── Public AZ-1: 10.0.1.0/24
├── Public AZ-2: 10.0.2.0/24
└── Public AZ-3: 10.0.3.0/24 (prod)

Subnets Privadas (App, DB, Cache):
├── Private AZ-1: 10.0.10.0/24
├── Private AZ-2: 10.0.11.0/24
└── Private AZ-3: 10.0.12.0/24 (prod)

Gateway Resources:
├── Internet Gateway → Tráfico público
├── NAT Gateway → Salida desde privadas
└── VPC Endpoints → S3 y CloudWatch sin salir VPC
```

**Security:**
- Private subnets sin acceso público
- NAT para salida controlada
- Security groups restrictivos por capa

### 2. Security (Security Module)

**Objetivo:** Gestionar autenticación, autorización y encriptación.

```
IAM Roles:
├── ecs_task_execution_role (push logs, get secrets)
├── ecs_task_role (S3, CloudWatch metrics)
└── rds_monitoring_role (Enhanced monitoring)

Security Groups (4 capas):
├── ALB SG → Puertos 80/443 públicos
├── App SG → Puerto 5050 solo desde ALB
├── DB SG → Puerto 5432 solo desde App
└── Cache SG → Puerto 6379 solo desde App

Encryption:
├── KMS Master Key (CMK)
│   ├── RDS at rest
│   ├── Redis at rest
│   ├── S3 at rest
│   └── Secrets Manager
└── TLS in transit (HTTPS, RDS SSL)

Secrets Manager:
├── Flask SECRET_KEY
├── DB master credentials
└── Anthropic API Key
```

**Compliance:**
- Encryption by default
- Least privilege access
- Audit logging habilitado
- MFA delete para S3 (prod)

### 3. Compute (Compute Module - ECS Fargate)

**Objetivo:** Ejecutar aplicación Flask con auto-scaling.

```
ECS Cluster: ticketdesk-{env}
│
├── Capacity Providers
│   ├── FARGATE (pago por segundo)
│   └── FARGATE_SPOT (50% descuento, preemptible)
│
└── Service: prod-ticketdesk-app-service
    ├── Task Definition
    │   ├── Image: {ECR}/ticketdesk:latest
    │   ├── CPU: 512/1024/2048 (por env)
    │   ├── Memory: 1024/2048/4096 (por env)
    │   ├── Port: 5050
    │   └── Logging: CloudWatch
    │
    ├── Desired Count
    │   ├── Dev: 1
    │   ├── Staging: 2
    │   └── Prod: 3-10 (auto-scaling)
    │
    └── Auto Scaling
        ├── Target Tracking CPU >70%
        └── Target Tracking Memory >80%
```

**Health Management:**
- Container health check (curl /api/health)
- ALB target group health check (30s interval)
- ECS deployment rollback (502 handling)
- Task replacement on failure

### 4. Database (Database Module - RDS)

**Objetivo:** PostgreSQL persistente con HA y backups.

```
RDS Instance: prod-ticketdesk-db
├── Engine: PostgreSQL 14+
├── Instance Class
│   ├── Dev: db.t3.micro (1vCPU, 1GB RAM)
│   ├── Staging: db.t3.small (1vCPU, 2GB RAM)
│   └── Prod: db.r5.large (2vCPU, 16GB RAM)
│
├── Storage
│   ├── Type: gp3 (SSD)
│   ├── Size: 20-500GB (por env)
│   ├── IOPS: 3000
│   └── Encryption: KMS
│
├── High Availability (Prod)
│   ├── Multi-AZ: Primary + Standby
│   ├── Automated failover: <2 min
│   └── Enhanced monitoring: every 60s
│
├── Backups
│   ├── Automated: Daily (dev), Hourly (prod)
│   ├── Retention: 7-30 días
│   ├── Window: 02:00-03:00 UTC
│   └── Copy to S3: Manual/Scheduled
│
└── Monitoring
    ├── CloudWatch Alarms (CPU, connections, storage)
    ├── Performance Insights (prod)
    └── Slow query log
```

**Database Setup:**
```sql
-- Aplicación crea automáticamente:
CREATE DATABASE ticketdesk;
CREATE SCHEMA tickets;
CREATE SCHEMA audit;

-- Tablas principales (auto-created):
├── users (LDAP/AD synced)
├── tickets (company-segregated)
├── comments (with versioning)
├── assignments
├── sla_tracking
├── token_blacklist (JWT revocation)
├── system_log (audit trail)
└── webhook_events
```

### 5. Cache (Cache Module - Redis)

**Objetivo:** Sesiones, blacklist JWT, caché de aplicación.

```
Redis Replication Group: prod-ticketdesk-redis
├── Engine: Redis 7.0
├── Node Type
│   ├── Dev: cache.t3.micro
│   ├── Staging: cache.t3.small
│   └── Prod: cache.r6g.xlarge
│
├── Cluster Configuration
│   ├── Dev: 1 node
│   ├── Staging: 2 nodes + failover
│   └── Prod: 3 nodes + multi-AZ
│
├── Features
│   ├── Automatic failover (prod)
│   ├── Auto-backup (7 day retention)
│   ├── Encryption at rest (AES-256)
│   └── Parameter group (maxmemory-policy: LRU)
│
└── Use Cases
    ├── User sessions (15 min TTL)
    ├── JWT blacklist (30-60 min TTL)
    ├── Bot knowledge base cache
    └── Real-time WebSocket broadcasts
```

**Monitoring:**
- CPU utilization
- Memory utilization
- Eviction rate (critical alert)
- Network throughput

### 6. Storage (Storage Module - S3)

**Objetivo:** Almacenar backups de BD, logs y assets.

```
S3 Bucket: {env}-ticketdesk-backups-{account-id}
├── Versioning: Enabled
├── Encryption: KMS (CMK)
├── ACL: Private (no public access)
│
├── Lifecycle Policy
│   ├── Transition to GLACIER after 30 days
│   ├── Delete noncurrent versions after 30 days
│   └── Auto-cleanup enabled
│
├── Logging
│   ├── Access logs → separate bucket
│   └── Server access logging enabled
│
├── Contents
│   ├── Database backups (JSON.gz)
│   ├── Application logs
│   └── Static assets (optional CDN)
│
└── Backup Structure
    ├── s3://bucket/db-backups/
    ├── s3://bucket/app-logs/
    └── s3://bucket/archives/ (GLACIER)
```

**Backup Strategy:**
```
Daily Backup Schedule:
├── 02:00 UTC: RDS automated snapshot
├── 02:30 UTC: Copy snapshot to S3
├── 03:00 UTC: Database consistency check
└── Retention: 30 copies rolling
```

### 7. Load Balancer (LB Module)

**Objetivo:** Distribuir tráfico HTTPS entre tasks ECS.

```
Application Load Balancer (ALB)
├── DNS: {env}-ticketdesk-alb-{hash}.us-east-1.elb.amazonaws.com
├── Subnets: Public AZ-1, AZ-2, AZ-3 (prod)
│
├── Listeners
│   ├── Port 80 (HTTP) → Redirect 301 to 443
│   └── Port 443 (HTTPS)
│       ├── Certificate: ACM
│       ├── SSL Policy: TLS 1.2+
│       └── Health check path: /api/health
│
├── Target Group
│   ├── Type: IP (Fargate)
│   ├── Protocol: HTTP → ECS:5050
│   ├── Health Check
│   │   ├── Interval: 30 seconds
│   │   ├── Timeout: 5 seconds
│   │   ├── Healthy: 2 successes
│   │   └── Unhealthy: 3 failures
│   └── Stickiness: 24 hours (lb_cookie)
│
└── Features
    ├── Cross-zone load balancing
    ├── Connection draining (30s)
    └── IPv6 support
```

**SSL/TLS:**
- Certificado ACM (auto-renew)
- TLS 1.2 mínimo
- Strong cipher suites
- HSTS header (opcional)

### 8. Monitoring (Monitoring Module)

**Objetivo:** Observabilidad completa del sistema.

```
CloudWatch Logs
├── /ecs/prod-ticketdesk-app (ECS logs)
├── /aws/rds/prod-ticketdesk-db (RDS logs)
├── /aws/elasticache/redis (Redis logs)
└── /aws/vpc/flowlogs (Network logs)

CloudWatch Metrics
├── ECS Service
│   ├── CPUUtilization (target: 70%)
│   ├── MemoryUtilization (target: 80%)
│   ├── RunningCount
│   └── DesiredCount
│
├── RDS Database
│   ├── CPUUtilization
│   ├── DatabaseConnections
│   ├── ReadLatency / WriteLatency
│   ├── FreeableMemory
│   └── BinLogDiskUsage
│
├── Redis
│   ├── EngineCPUUtilization
│   ├── DatabaseMemoryUsagePercentage
│   ├── Evictions (critical)
│   └── NetworkBytesIn/Out
│
└── ALB
    ├── TargetResponseTime
    ├── RequestCount
    ├── HealthyHostCount / UnHealthyHostCount
    └── HTTPCode_Target_4XX/5XX

CloudWatch Alarms
├── ECS: High CPU (>85%), High Memory (>90%), Task count mismatch
├── RDS: High CPU, Low storage, High connections, High latency
├── Redis: High memory, Evictions, Node failures
└── ALB: 5XX errors, Unhealthy targets, High response time

CloudWatch Dashboard
└── prod-ticketdesk (visualización integrada)
```

**Query Examples:**
```
Error Rate:
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() as error_count

Latency P99:
fields @duration
| filter @duration > 0
| stats pct(@duration, 99) as p99

Slow Queries:
fields @timestamp, @queryDuration, @query
| filter @queryDuration > 1000
| sort @queryDuration desc
```

---

## Data Flow

### Request Flow (Happy Path)

```
1. User request
   ↓
2. ALB (HTTPS)
   ├─ SSL/TLS termination
   └─ Health check validation
   ↓
3. ECS Task (Flask)
   ├─ Authentication (LDAP/AD)
   ├─ Authorization (RBAC)
   └─ Request logging
   ↓
4. Database (RDS PostgreSQL)
   ├─ Query execution
   ├─ Connection pooling
   └─ Encryption at rest
   ↓
5. Cache (Redis)
   ├─ Session storage
   ├─ JWT blacklist lookup
   └─ Response caching
   ↓
6. Response back to user (HTML, JSON, WebSocket)
```

### Backup Flow

```
Daily at 02:00 UTC
│
├─ RDS Automated Snapshot (AWS managed)
│  └─ Encrypted with KMS
│
├─ Application Backup Export
│  ├─ Export RDS snapshot to S3
│  ├─ Compress with gzip
│  └─ Encrypt with KMS
│
├─ S3 Versioning
│  ├─ Keep 30 days rolling
│  └─ Transition to GLACIER after 30 days
│
└─ Notification (SNS)
   └─ Email to on-call team
```

### Auto-Scaling Flow

```
Metric Observation (every 5 min)
│
├─ CPU Utilization > 70%
│  └─ Scale UP: Add task (+1)
│
├─ Memory Utilization > 80%
│  └─ Scale UP: Add task (+1)
│
└─ Resource utilization < 50%
   └─ Scale DOWN: Remove task (-1, after 5 min cooldown)

Constraints:
├─ Min: 1 (dev) / 2 (staging) / 3 (prod)
└─ Max: 2 (dev) / 4 (staging) / 10 (prod)
```

---

## Security Layers

```
Layer 1: Network
├─ Internet Gateway (public access)
├─ NAT Gateway (private egress)
├─ VPC Endpoints (no internet exposure)
└─ Security Groups (port-level access)

Layer 2: Transport
├─ HTTPS/TLS (ALB to client)
├─ Encrypted RDS connection
├─ Redis encryption in transit
└─ VPC internal (private IPs)

Layer 3: Application
├─ LDAP/AD authentication
├─ RBAC authorization
├─ JWT with blacklist revocation
└─ Input validation/sanitization

Layer 4: Data
├─ RDS encryption at rest (KMS)
├─ Redis encryption at rest (AES-256)
├─ S3 encryption at rest (KMS)
├─ Secrets Manager (encrypted)
└─ Parameter group (max connections, timeouts)

Layer 5: Audit
├─ VPC Flow Logs (network traffic)
├─ RDS audit logs
├─ CloudTrail (AWS API calls)
├─ Application logs (system_log table)
└─ ALB access logs
```

---

## Cost Breakdown (Monthly Estimate)

### Development
```
ECS Fargate:     $  5  (1×0.5vCPU, 1GB RAM)
RDS db.t3.micro: $ 10  (single-AZ)
Redis t3.micro:  $  5  (1 node)
S3 (backups):    $  2  (minimal storage)
ALB:             $ 16  (minimum)
CloudWatch:      $  5  (logs, metrics)
─────────────────────
Total:           $ 43/month
```

### Staging
```
ECS Fargate:     $ 25  (2×0.5vCPU, 2GB RAM)
RDS db.t3.small: $ 30  (multi-AZ)
Redis t3.small:  $ 15  (2 nodes)
S3 (backups):    $ 10  (daily snapshots)
ALB:             $ 16
CloudWatch:      $ 10
NAT Gateway:     $ 35
─────────────────────
Total:           $141/month
```

### Production
```
ECS Fargate:     $100  (3×1vCPU, 2GB RAM avg, auto-scale to 10)
RDS r5.large:    $150  (multi-AZ, 500GB)
Redis r6g.xlarge:$ 400  (3 nodes, multi-AZ)
S3 (backups):    $ 50  (hourly snapshots, archives)
ALB:             $ 16
CloudWatch:      $ 30  (Performance Insights, enhanced monitoring)
NAT Gateway:     $ 35
CloudFront:      $ 20  (if CDN enabled)
Data Transfer:   $ 50  (inter-AZ, internet)
─────────────────────
Total:           $851/month

* With reserved instances: -40% → ~$500/month
* With Savings Plans: -30% → ~$600/month
```

---

## High Availability

### RDS PostgreSQL
- **Multi-AZ:** Primary in AZ-1, Standby in AZ-2
- **Automatic Failover:** <2 minutes
- **Monitoring:** CPU, connections, latency
- **Backup:** Daily snapshots, 30-day retention

### Redis
- **Multi-node:** 1 (dev) → 3 (prod)
- **Automatic Failover:** Cluster mode enabled
- **Replication:** Async across AZs
- **Backup:** Snapshots every 24 hours

### ECS Service
- **Deployment Strategy:** Rolling (100% min healthy)
- **Desired Count:** 1 (dev) → 3 (prod)
- **Auto Scaling:** CPU/Memory based
- **Health Checks:** ALB + ECS task level

### Disaster Recovery
- **RTO (Recovery Time Objective):** <5 minutes
- **RPO (Recovery Point Objective):** <1 hour
- **Backup Locations:** 3 AZs via S3
- **Cross-Region:** Enabled (optional)

---

## Environment Comparison

| Feature | Dev | Staging | Prod |
|---------|-----|---------|------|
| **Availability Zones** | 1 | 2 | 3 |
| **ECS Tasks** | 1 | 2-4 | 3-10 |
| **RDS Instance** | db.t3.micro | db.t3.small | db.r5.large |
| **RDS Multi-AZ** | No | Yes | Yes |
| **Redis Nodes** | 1 | 2 | 3 |
| **HTTPS** | No | Yes | Yes |
| **Performance Insights** | No | No | Yes |
| **CloudFront CDN** | No | Yes | Yes |
| **WAF** | No | Yes | Yes |
| **Estimated Cost** | $43 | $141 | $851 |

---

## Deployment Commands Quick Reference

```bash
# Initialization
cd terraform && terraform init

# Development
terraform apply -var-file=environments/dev/terraform.tfvars

# Staging
terraform apply -var-file=environments/staging/terraform.tfvars

# Production (with approval)
terraform apply -var-file=environments/prod/terraform.tfvars

# Get outputs
terraform output -json > outputs.json

# Destroy (careful!)
terraform destroy -var-file=environments/prod/terraform.tfvars
```

---

**Documento:** Infrastructure Overview
**Versión:** 2.1
**Actualizado:** 2026-05-29
**Mantenedor:** TicketDesk Team
