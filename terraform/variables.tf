# ====================================================================
# TicketDesk Enterprise - Variable Definitions
# ====================================================================
# Todas las variables configurables para soportar multi-ambiente

# ====================================================================
# AWS & General
# ====================================================================
variable "aws_region" {
  description = "AWS region para desplegar recursos"
  type        = string
  default     = "us-east-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-\\d{1}$", var.aws_region))
    error_message = "AWS region debe ser válida (ej: us-east-1)."
  }
}

variable "environment" {
  description = "Ambiente: dev, staging, prod"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment debe ser dev, staging o prod."
  }
}

variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
  default     = "ticketdesk"

  validation {
    condition     = length(var.project_name) <= 20
    error_message = "Project name debe tener máximo 20 caracteres."
  }
}

# ====================================================================
# VPC Networking
# ====================================================================
variable "vpc_cidr" {
  description = "CIDR block para VPC"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR debe ser un bloque CIDR válido."
  }
}

variable "availability_zones" {
  description = "Zonas de disponibilidad"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]

  validation {
    condition     = length(var.availability_zones) >= 2 && length(var.availability_zones) <= 4
    error_message = "Debe haber entre 2 y 4 availability zones."
  }
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks para subnets públicas (ALB)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) >= 2
    error_message = "Debe haber mínimo 2 subnets públicas para alta disponibilidad."
  }
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks para subnets privadas (App, DB)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]

  validation {
    condition     = length(var.private_subnet_cidrs) >= 2
    error_message = "Debe haber mínimo 2 subnets privadas para alta disponibilidad."
  }
}

variable "enable_nat_gateway" {
  description = "Habilitar NAT Gateway para salida desde subnets privadas"
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "Habilitar VPC Flow Logs para auditoría"
  type        = bool
  default     = true
}

# ====================================================================
# Database (RDS PostgreSQL)
# ====================================================================
variable "db_instance_class" {
  description = "Clase de instancia RDS (dev: db.t3.micro, staging: db.t3.small, prod: db.r5.large)"
  type        = string

  validation {
    condition     = can(regex("^db\\.[a-z0-9]+\\.[a-z]+$", var.db_instance_class))
    error_message = "DB instance class debe ser válida (ej: db.t3.micro)."
  }
}

variable "db_allocated_storage" {
  description = "Almacenamiento inicial RDS en GB"
  type        = number
  default     = 100

  validation {
    condition     = var.db_allocated_storage >= 20 && var.db_allocated_storage <= 65536
    error_message = "DB storage debe estar entre 20 y 65536 GB."
  }
}

variable "db_engine_version" {
  description = "PostgreSQL versión (14+)"
  type        = string
  default     = "14.9"
}

variable "db_backup_retention_days" {
  description = "Días de retención de backups automáticos"
  type        = number
  default     = 30

  validation {
    condition     = var.db_backup_retention_days >= 7 && var.db_backup_retention_days <= 35
    error_message = "Retención debe estar entre 7 y 35 días."
  }
}

variable "db_backup_window" {
  description = "Ventana de backup (UTC, formato HH:MM-HH:MM)"
  type        = string
  default     = "02:00-03:00"
}

variable "db_maintenance_window" {
  description = "Ventana de mantenimiento (formato: ddd:HH:MM-ddd:HH:MM)"
  type        = string
  default     = "sun:03:00-sun:04:00"
}

variable "multi_az" {
  description = "Multi-AZ deployment para RDS (HA)"
  type        = bool
  default     = true
}

variable "db_publicly_accessible" {
  description = "Permitir acceso público a RDS (solo para dev, nunca prod)"
  type        = bool
  default     = false

  validation {
    condition     = !(var.db_publicly_accessible && var.environment == "prod")
    error_message = "No se permite acceso público a BD en producción."
  }
}

# ====================================================================
# Cache (ElastiCache Redis)
# ====================================================================
variable "redis_node_type" {
  description = "Tipo de nodo Redis (cache.t3.micro, cache.t3.small, cache.r6g.large)"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Número de nodos Redis"
  type        = number
  default     = 2

  validation {
    condition     = var.redis_num_cache_nodes >= 1 && var.redis_num_cache_nodes <= 6
    error_message = "Redis nodes debe estar entre 1 y 6."
  }
}

variable "redis_automatic_failover" {
  description = "Habilitar failover automático para Redis cluster"
  type        = bool
  default     = true
}

variable "redis_automatic_backup" {
  description = "Habilitar backups automáticos de Redis"
  type        = bool
  default     = true
}

variable "redis_snapshot_retention_days" {
  description = "Días de retención de snapshots Redis"
  type        = number
  default     = 7

  validation {
    condition     = var.redis_snapshot_retention_days >= 1 && var.redis_snapshot_retention_days <= 35
    error_message = "Retención debe estar entre 1 y 35 días."
  }
}

# ====================================================================
# Storage (S3)
# ====================================================================
variable "backup_retention_days" {
  description = "Días de retención de backups en S3"
  type        = number
  default     = 30

  validation {
    condition     = var.backup_retention_days >= 7 && var.backup_retention_days <= 2555
    error_message = "Retención debe estar entre 7 y 2555 días."
  }
}

variable "enable_versioning" {
  description = "Habilitar versionado de objetos S3"
  type        = bool
  default     = true
}

variable "enable_encryption" {
  description = "Habilitar encriptación en reposo con KMS"
  type        = bool
  default     = true
}

variable "enable_lifecycle_policy" {
  description = "Habilitar políticas de ciclo de vida en S3"
  type        = bool
  default     = true
}

variable "mfa_delete_required" {
  description = "Requerir MFA para eliminar objetos versionados (solo prod)"
  type        = bool
  default     = false
}

# ====================================================================
# Security & Compliance
# ====================================================================
variable "kms_enable_rotation" {
  description = "Habilitar rotación automática de claves KMS"
  type        = bool
  default     = true
}

variable "allowed_admin_cidrs" {
  description = "CIDR blocks permitidos para acceso administrativo (SSH, Bastion)"
  type        = list(string)
  default     = ["0.0.0.0/0"] # NOTA: Restringir en producción

  validation {
    condition     = alltrue([for cidr in var.allowed_admin_cidrs : can(cidrhost(cidr, 0))])
    error_message = "Todos los valores deben ser bloques CIDR válidos."
  }
}

# ====================================================================
# Load Balancer
# ====================================================================
variable "enable_https" {
  description = "Habilitar HTTPS (requiere certificate_arn)"
  type        = bool
  default     = true
}

variable "acm_certificate_arn" {
  description = "ARN del certificado ACM para HTTPS"
  type        = string
  default     = ""
  sensitive   = true
}

variable "app_port" {
  description = "Puerto de aplicación Flask (default 5050)"
  type        = number
  default     = 5050

  validation {
    condition     = var.app_port >= 1024 && var.app_port <= 65535
    error_message = "Puerto debe estar entre 1024 y 65535."
  }
}

# ====================================================================
# Compute (ECS Fargate)
# ====================================================================
variable "container_image" {
  description = "Docker image para TicketDesk (ej: 123456789.dkr.ecr.us-east-1.amazonaws.com/ticketdesk:latest)"
  type        = string

  validation {
    condition     = length(var.container_image) > 0
    error_message = "Container image es requerida."
  }
}

variable "task_cpu" {
  description = "CPU para task (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 512

  validation {
    condition     = contains([256, 512, 1024, 2048, 4096], var.task_cpu)
    error_message = "CPU debe ser 256, 512, 1024, 2048 o 4096."
  }
}

variable "task_memory" {
  description = "Memoria para task en MB (512-30720)"
  type        = number
  default     = 1024

  validation {
    condition     = var.task_memory >= 512 && var.task_memory <= 30720
    error_message = "Memoria debe estar entre 512 y 30720 MB."
  }
}

variable "ecs_desired_count" {
  description = "Número deseado de tasks (mínimo 2 para HA)"
  type        = number
  default     = 2

  validation {
    condition     = var.ecs_desired_count >= 1 && var.ecs_desired_count <= 10
    error_message = "Desired count debe estar entre 1 y 10."
  }
}

variable "ecs_min_capacity" {
  description = "Mínimo de tasks en auto scaling"
  type        = number
  default     = 2
}

variable "ecs_max_capacity" {
  description = "Máximo de tasks en auto scaling"
  type        = number
  default     = 6

  validation {
    condition     = var.ecs_max_capacity >= var.ecs_min_capacity
    error_message = "Max capacity debe ser >= min capacity."
  }
}

# ====================================================================
# Monitoring & Logging
# ====================================================================
variable "cloudwatch_log_retention" {
  description = "Días de retención de logs CloudWatch"
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.cloudwatch_log_retention)
    error_message = "Debe ser un valor válido de retención CloudWatch."
  }
}

variable "cpu_threshold" {
  description = "Umbral de alerta para CPU (%)"
  type        = number
  default     = 80

  validation {
    condition     = var.cpu_threshold > 0 && var.cpu_threshold <= 100
    error_message = "CPU threshold debe estar entre 0 y 100."
  }
}

variable "memory_threshold" {
  description = "Umbral de alerta para memoria (%)"
  type        = number
  default     = 85

  validation {
    condition     = var.memory_threshold > 0 && var.memory_threshold <= 100
    error_message = "Memory threshold debe estar entre 0 y 100."
  }
}

variable "db_latency_threshold" {
  description = "Umbral de alerta para latencia DB (ms)"
  type        = number
  default     = 500

  validation {
    condition     = var.db_latency_threshold > 0
    error_message = "DB latency threshold debe ser > 0."
  }
}

variable "enable_performance_insights" {
  description = "Habilitar Performance Insights en RDS"
  type        = bool
  default     = false
}

# ====================================================================
# Notifications
# ====================================================================
variable "alert_email" {
  description = "Email para recibir alertas CloudWatch"
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.alert_email))
    error_message = "Alert email debe ser un email válido."
  }
}

# ====================================================================
# Optional Features
# ====================================================================
variable "enable_cdn" {
  description = "Habilitar CloudFront CDN para assets estáticos"
  type        = bool
  default     = false
}

variable "enable_waf" {
  description = "Habilitar AWS WAF para protección DDoS/XSS"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags adicionales para todos los recursos"
  type        = map(string)
  default = {
    Owner      = "TicketDesk Team"
    CostCenter = "IT Operations"
  }
}
