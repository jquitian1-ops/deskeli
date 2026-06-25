# ====================================================================
# Storage Module - Variables
# ====================================================================

variable "environment" {
  description = "Ambiente: dev, staging, prod"
  type        = string
}

variable "backup_retention_days" {
  description = "Días de retención de backups"
  type        = number
}

variable "enable_versioning" {
  description = "Habilitar versionado"
  type        = bool
}

variable "enable_encryption" {
  description = "Habilitar encriptación KMS"
  type        = bool
}

variable "kms_key_id" {
  description = "KMS key para encriptación"
  type        = string
}

variable "enable_lifecycle_policy" {
  description = "Habilitar políticas de ciclo de vida"
  type        = bool
}

variable "mfa_delete_required" {
  description = "Requerir MFA para delete (solo prod)"
  type        = bool
  default     = false
}
