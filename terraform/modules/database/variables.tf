# ====================================================================
# Database Module - Variables
# ====================================================================

variable "environment" {
  description = "Ambiente: dev, staging, prod"
  type        = string
}

variable "db_instance_class" {
  description = "Clase de instancia RDS"
  type        = string
}

variable "db_allocated_storage" {
  description = "Almacenamiento inicial en GB"
  type        = number
}

variable "db_engine_version" {
  description = "Versión de PostgreSQL"
  type        = string
}

variable "db_backup_retention_days" {
  description = "Días de retención de backups"
  type        = number
}

variable "db_backup_window" {
  description = "Ventana de backup en UTC"
  type        = string
}

variable "db_maintenance_window" {
  description = "Ventana de mantenimiento"
  type        = string
}

variable "multi_az" {
  description = "Habilitar Multi-AZ"
  type        = bool
}

variable "publicly_accessible" {
  description = "Permitir acceso público"
  type        = bool
  default     = false
}

variable "vpc_id" {
  description = "ID de la VPC"
  type        = string
}

variable "db_subnet_group_name" {
  description = "Nombre del DB subnet group"
  type        = string
}

variable "db_security_group_id" {
  description = "Security group para RDS"
  type        = string
}

variable "kms_key_id" {
  description = "KMS key para encriptación"
  type        = string
}

variable "monitoring_interval" {
  description = "Intervalo de monitoreo (0=deshabilitado, 60-3600)"
  type        = number
  default     = 60
}

variable "monitoring_role_arn" {
  description = "ARN del rol de monitoreo RDS"
  type        = string
}

variable "enable_performance_insights" {
  description = "Habilitar Performance Insights"
  type        = bool
  default     = false
}
