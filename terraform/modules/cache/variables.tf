# ====================================================================
# Cache Module - Variables
# ====================================================================

variable "environment" {
  description = "Ambiente: dev, staging, prod"
  type        = string
}

variable "redis_node_type" {
  description = "Tipo de nodo Redis"
  type        = string
}

variable "redis_num_cache_nodes" {
  description = "Número de nodos"
  type        = number
}

variable "redis_automatic_failover" {
  description = "Habilitar failover automático"
  type        = bool
}

variable "redis_automatic_backup" {
  description = "Habilitar backups automáticos"
  type        = bool
}

variable "redis_snapshot_retention_days" {
  description = "Días de retención de snapshots"
  type        = number
}

variable "vpc_id" {
  description = "ID de la VPC"
  type        = string
}

variable "subnet_ids" {
  description = "IDs de subnets privadas"
  type        = list(string)
}

variable "cache_security_group_id" {
  description = "Security group para Redis"
  type        = string
}

variable "kms_key_id" {
  description = "KMS key para encriptación"
  type        = string
}
