# TicketDesk Terraform - Índice Completo

Guía de navegación por toda la documentación y código generado.

## Inicio Rápido (Elige Tu Camino)

### Si tienes 5 minutos
→ **[QUICK_START.md](QUICK_START.md)** - Inicio en 5 pasos

### Si tienes 30 minutos
→ **[README.md](README.md)** - Guía completa de inicio

### Si necesitas entender la arquitectura
→ **[INFRASTRUCTURE_OVERVIEW.md](INFRASTRUCTURE_OVERVIEW.md)** - Diagramas y componentes

### Si vas a desplegar en producción
→ **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Paso a paso detallado

### Si acabas de desplegar
→ **[TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)** - Validación post-deployment

### Si necesitas conexión strings
→ **[OUTPUTS_REFERENCE.md](OUTPUTS_REFERENCE.md)** - Referencia de todos los outputs

---

## Estructura del Proyecto

```
terraform/
├── 📄 main.tf                           Root module (orquestación)
├── 📄 variables.tf                      Variables de entrada (48 variables)
├── 📄 outputs.tf                        Valores de salida (40+ outputs)
├── 📄 terraform.tfvars                  Valores globales por defecto
├── 📄 .gitignore                        Exclusiones para Git
│
├── 📚 Documentación (6 archivos)
│   ├── 📄 QUICK_START.md               ← COMIENZA AQUÍ (5 min)
│   ├── 📄 README.md
│   ├── 📄 DEPLOYMENT_GUIDE.md
│   ├── 📄 INFRASTRUCTURE_OVERVIEW.md
│   ├── 📄 OUTPUTS_REFERENCE.md
│   ├── 📄 TESTING_CHECKLIST.md
│   └── 📄 INDEX.md                      (este archivo)
│
├── modules/                             (8 módulos reutilizables)
│   ├── vpc/
│   │   ├── main.tf                      VPC, subnets, NAT, VPC Endpoints
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── security/
│   │   ├── main.tf                      IAM, KMS, Secrets, Security Groups
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── database/
│   │   ├── main.tf                      RDS PostgreSQL 14+
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── cache/
│   │   ├── main.tf                      ElastiCache Redis 7.0
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── storage/
│   │   ├── main.tf                      S3 para backups
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── lb/
│   │   ├── main.tf                      ALB con HTTPS
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── compute/
│   │   ├── main.tf                      ECS Fargate con auto-scaling
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   └── monitoring/
│       ├── main.tf                      CloudWatch dashboards & alarms
│       ├── variables.tf
│       └── outputs.tf
│
└── environments/                        (3 ambientes preconfigurados)
    ├── dev/terraform.tfvars             Desarrollo (~$43/mes)
    ├── staging/terraform.tfvars         Staging (~$141/mes)
    └── prod/terraform.tfvars            Producción (~$851/mes)
```

---

## Archivos Terraform Principales

### Root Module (`main.tf`)
- **Líneas:** ~500
- **Propósito:** Orquestar todos los módulos
- **Contenido:**
  - Configuración de provider AWS
  - Invocación de módulos
  - Auto-scaling policies
  - SNS topics
  - CloudFront CDN (opcional)

### Variables (`variables.tf`)
- **Líneas:** ~300
- **Propósito:** Definir todas las variables de entrada
- **Contenido:**
  - 48 variables totales
  - Validaciones por tipo
  - Restricciones de rango
  - Mensajes de error descriptivos

### Outputs (`outputs.tf`)
- **Líneas:** ~200
- **Propósito:** Exportar valores útiles
- **Contenido:**
  - 40+ outputs
  - Connection strings
  - URLs de consola AWS
  - ARNs de recursos

### Variables por Ambiente (`environments/*/terraform.tfvars`)
- **Dev:** Configuración mínima, single-AZ
- **Staging:** HA, multi-AZ, HTTPS
- **Prod:** Full redundancy, 3 AZs, performance

---

## Módulos Detallados

### 1. VPC Module (`modules/vpc/`)
**Responsabilidad:** Networking

```
├── main.tf (250 líneas)
│   ├── VPC CIDR flexible
│   ├── Public subnets (ALB)
│   ├── Private subnets (App, DB)
│   ├── Internet Gateway
│   ├── NAT Gateway (configurable)
│   ├── Route tables (público/privado)
│   ├── VPC Endpoints (S3, Logs)
│   └── Flow Logs (auditoría)
├── variables.tf (30 líneas)
└── outputs.tf (35 líneas)
```

**Usa este módulo para:** Crear infraestructura de red aislada

---

### 2. Security Module (`modules/security/`)
**Responsabilidad:** IAM, KMS, Secrets

```
├── main.tf (400 líneas)
│   ├── KMS Master Key
│   ├── ECS Task Roles (2)
│   ├── RDS Monitoring Role
│   ├── Security Groups (4)
│   │   ├── ALB SG
│   │   ├── App SG
│   │   ├── DB SG
│   │   └── Cache SG
│   └── Secrets Manager (3)
│       ├── Flask SECRET_KEY
│       ├── DB Credentials
│       └── Anthropic API Key
├── variables.tf (25 líneas)
└── outputs.tf (50 líneas)
```

**Usa este módulo para:** Gestionar seguridad y credenciales

---

### 3. Database Module (`modules/database/`)
**Responsabilidad:** RDS PostgreSQL

```
├── main.tf (300 líneas)
│   ├── RDS Instance (flexible class/storage)
│   ├── Parameter Group (tuned)
│   ├── Option Group
│   ├── DB Subnet Group
│   ├── Enhanced Monitoring
│   └── CloudWatch Alarms (3)
├── variables.tf (35 líneas)
└── outputs.tf (25 líneas)
```

**Usa este módulo para:** Desplegar BD persistente

---

### 4. Cache Module (`modules/cache/`)
**Responsabilidad:** Redis Cluster

```
├── main.tf (250 líneas)
│   ├── ElastiCache Subnet Group
│   ├── Parameter Group
│   ├── Replication Group (multi-node)
│   ├── CloudWatch Log Groups (2)
│   ├── SNS Topic
│   └── CloudWatch Alarms (3)
├── variables.tf (30 líneas)
└── outputs.tf (25 líneas)
```

**Usa este módulo para:** Cache de sesiones y JWT blacklist

---

### 5. Storage Module (`modules/storage/`)
**Responsabilidad:** S3 Backups

```
├── main.tf (250 líneas)
│   ├── S3 Bucket (principal)
│   ├── S3 Bucket (logs)
│   ├── Versionado
│   ├── Encriptación KMS
│   ├── Logging
│   ├── Lifecycle Policies
│   ├── CORS
│   ├── Bucket Policy
│   └── CloudWatch Alarm
├── variables.tf (25 líneas)
└── outputs.tf (20 líneas)
```

**Usa este módulo para:** Almacenar backups automáticos

---

### 6. Load Balancer Module (`modules/lb/`)
**Responsabilidad:** ALB HTTPS

```
├── main.tf (250 líneas)
│   ├── Application Load Balancer
│   ├── Target Group
│   ├── HTTP Listener (redirect)
│   ├── HTTPS Listener (TLS 1.2+)
│   ├── Listener Rules
│   └── CloudWatch Alarms (3)
├── variables.tf (30 líneas)
└── outputs.tf (20 líneas)
```

**Usa este módulo para:** Distribuir tráfico HTTPS

---

### 7. Compute Module (`modules/compute/`)
**Responsabilidad:** ECS Fargate

```
├── main.tf (400 líneas)
│   ├── CloudWatch Log Group
│   ├── ECS Cluster
│   ├── Capacity Providers
│   ├── Task Definition
│   ├── ECS Service
│   ├── Auto Scaling Target
│   ├── Auto Scaling Policies (2)
│   └── CloudWatch Alarms (3)
├── variables.tf (40 líneas)
└── outputs.tf (20 líneas)
```

**Usa este módulo para:** Ejecutar aplicación Flask

---

### 8. Monitoring Module (`modules/monitoring/`)
**Responsabilidad:** CloudWatch

```
├── main.tf (350 líneas)
│   ├── CloudWatch Dashboard
│   ├── CloudWatch Alarms (9)
│   │   ├── ECS (4)
│   │   ├── RDS (2)
│   │   ├── Application (2)
│   │   └── ALB (1)
│   └── Log Query Definitions (2)
├── variables.tf (25 líneas)
└── outputs.tf (15 líneas)
```

**Usa este módulo para:** Observabilidad completa

---

## Documentación en Detalle

### README.md
- Estructura del proyecto
- Requisitos previos
- Inicio rápido (5 pasos)
- Configuración por ambiente
- Variables importantes
- Operaciones comunes
- Backend remoto (S3)
- Cost optimization
- Troubleshooting

**Secciones principales:**
1. Requisitos
2. Estructura
3. Inicio rápido
4. Configuración por ambiente
5. Variables
6. Operaciones
7. Cost optimization

---

### QUICK_START.md
- 5 pasos ultra-rápidos
- Verificación post-despliegue
- Cambiar entre ambientes
- Troubleshooting básico
- Limpiar/destruir
- Comandos útiles

**Duración:** ~5 minutos

---

### DEPLOYMENT_GUIDE.md
- Requisitos detallados
- Setup ECR Docker
- Certificado HTTPS
- Inicializar Terraform
- Configurar variables
- Planificar despliegue
- Aplicar infraestructura
- Obtener connection strings
- Configurar Secrets Manager
- Verificación post-deploy
- Monitoreo
- Troubleshooting
- Actualización infraestructura
- Restauración

**Duración:** ~1 hora

---

### INFRASTRUCTURE_OVERVIEW.md
- Diagrama ASCII de arquitectura
- 8 componentes principales
- Data flow (request y backup)
- Auto-scaling flow
- 5 capas de seguridad
- Cost breakdown por ambiente
- High availability strategy
- Disaster recovery
- Environment comparison
- Quick reference commands

---

### OUTPUTS_REFERENCE.md
- Cómo obtener outputs
- VPC outputs (conexión networking)
- Load Balancer outputs (DNS, ARN)
- ECS outputs (cluster, service, logs)
- Database outputs (connection string)
- Cache outputs (Redis endpoint)
- Storage outputs (S3 bucket)
- Security outputs (KMS, IAM, SGs)
- Monitoring outputs (dashboard, alarms)
- Utility outputs (environment, region)
- Script para exportar .env
- Ejemplo completo de iniciar app

---

### TESTING_CHECKLIST.md
- Pre-deployment (validación código)
- Post-deployment (infraestructura)
  - VPC & networking
  - Load balancer
  - ECS cluster
  - RDS database
  - Redis cache
  - S3 storage
- Security validation (IAM, SGs, KMS)
- Monitoring & logging
- Performance baseline
- Load testing
- Disaster recovery testing
  - RDS failover
  - Database restore
  - S3 backup restore
- Final checklist

---

## Variables Principales

### Network
- `vpc_cidr` - CIDR de VPC
- `availability_zones` - AZs a usar
- `public_subnet_cidrs` - Subnets públicas
- `private_subnet_cidrs` - Subnets privadas
- `enable_nat_gateway` - Habilitar NAT

### Database
- `db_instance_class` - Tamaño (t3.micro → r5.large)
- `db_allocated_storage` - GB (20-500)
- `db_backup_retention_days` - Días (7-35)
- `multi_az` - Alta disponibilidad

### Cache
- `redis_node_type` - Tamaño (t3.micro → r6g.xlarge)
- `redis_num_cache_nodes` - Nodos (1-6)
- `redis_automatic_failover` - Failover automático

### Compute
- `container_image` - Docker image ECR
- `task_cpu` - CPU (256-4096)
- `task_memory` - Memoria MB (512-30720)
- `ecs_desired_count` - Tasks deseadas
- `ecs_min_capacity` - Tasks mínimas
- `ecs_max_capacity` - Tasks máximas

### Security
- `enable_https` - HTTPS/TLS
- `acm_certificate_arn` - Certificado ACM
- `allowed_admin_cidrs` - CIDRs admin
- `kms_enable_rotation` - Rotación KMS

---

## Outputs Clave

Después de `terraform apply`, obtienes:

```
vpc_id                          → ID de VPC
alb_dns_name                    → DNS del balanceador
alb_zone_id                     → Zone ID para Route53
ecs_cluster_name                → Nombre del cluster
ecs_service_name                → Nombre del servicio
database_connection_string      → PostgreSQL connection
redis_connection_string         → Redis connection
backup_bucket_name              → S3 bucket name
kms_key_id                       → KMS key ID
dashboard_url                   → CloudWatch dashboard
```

---

## Flujo Recomendado de Lectura

```
1. QUICK_START.md (5 min)
   ├─ Entender pasos básicos
   └─ Verificar requisitos

2. README.md (15 min)
   ├─ Estructura del proyecto
   ├─ Variables por ambiente
   └─ Operaciones comunes

3. INFRASTRUCTURE_OVERVIEW.md (20 min)
   ├─ Entender arquitectura
   ├─ Ver diagramas
   └─ Revisar componentes

4. DEPLOYMENT_GUIDE.md (30 min)
   ├─ Preparar prerequisites
   ├─ Configurar variables
   ├─ Step-by-step deployment
   └─ Post-deployment setup

5. TESTING_CHECKLIST.md (15 min)
   ├─ Validar infraestructura
   ├─ Test de conectividad
   └─ Verificar security

6. OUTPUTS_REFERENCE.md (10 min)
   ├─ Obtener connection strings
   ├─ Crear .env de app
   └─ Setup inicial
```

**Tiempo total:** ~95 minutos lectura + 30 minutos deploy = **2 horas**

---

## Cheat Sheet de Comandos

```bash
# Inicializar
terraform init

# Validar
terraform validate
terraform fmt -recursive

# Plan
terraform plan -var-file=environments/dev/terraform.tfvars
terraform plan -var-file=environments/dev/terraform.tfvars -out=tfplan

# Apply
terraform apply -var-file=environments/dev/terraform.tfvars
terraform apply tfplan

# Outputs
terraform output
terraform output -json > outputs.json
terraform output -raw alb_dns_name

# State
terraform state list
terraform state show aws_db_instance.main
terraform state pull > backup.tfstate

# Destroy
terraform destroy -var-file=environments/dev/terraform.tfvars

# Debugging
TF_LOG=DEBUG terraform plan
terraform validate -json
```

---

## FAQs

### ¿Por dónde empiezo?
→ Lee **QUICK_START.md**

### ¿Cómo conecto la app a la BD?
→ Lee **OUTPUTS_REFERENCE.md**, sección "Database"

### ¿Por qué me dice que falta un certificado?
→ Lee **DEPLOYMENT_GUIDE.md**, sección "Certificado HTTPS"

### ¿Cómo valido que está bien desplegado?
→ Consulta **TESTING_CHECKLIST.md**

### ¿Cuánto cuesta?
→ Lee **INFRASTRUCTURE_OVERVIEW.md**, sección "Cost Breakdown"

### ¿Cómo cambio el tamaño de RDS?
→ Lee **README.md**, sección "Actualizar Database"

### ¿Dónde veo los logs?
→ Lee **OUTPUTS_REFERENCE.md**, sección "CloudWatch Logs"

### ¿Cómo hago disaster recovery?
→ Lee **TESTING_CHECKLIST.md**, sección "Disaster Recovery"

---

## Estructura de Directorios Aún Mejor

```
terraform/ (41 archivos, 2,500+ líneas Terraform)
│
├─ 📋 Documentación (6 archivos)
│  ├─ QUICK_START.md            ← Empieza aquí
│  ├─ README.md
│  ├─ DEPLOYMENT_GUIDE.md
│  ├─ INFRASTRUCTURE_OVERVIEW.md
│  ├─ OUTPUTS_REFERENCE.md
│  └─ TESTING_CHECKLIST.md
│
├─ 🔧 Root Module (4 archivos)
│  ├─ main.tf                   ← Orquestación
│  ├─ variables.tf              ← Entrada
│  ├─ outputs.tf                ← Salida
│  └─ terraform.tfvars
│
├─ 📦 Modules (24 archivos en 8 carpetas)
│  └─ vpc/, security/, database/, cache/, storage/, lb/, compute/, monitoring/
│
└─ ⚙️ Environments (3 archivos)
   ├─ environments/dev/terraform.tfvars
   ├─ environments/staging/terraform.tfvars
   └─ environments/prod/terraform.tfvars
```

---

## Links Útiles

- [AWS Terraform Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Documentation](https://www.terraform.io/docs)
- [TicketDesk CLAUDE.md](../CLAUDE.md) - Requisitos del proyecto

---

**Este es tu mapa de navegación. ¡Bienvenido a la infraestructura de TicketDesk!**

Última actualización: 2026-05-29
