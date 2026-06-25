# ====================================================================
# Security Module - Variables
# ====================================================================

variable "environment" {
  description = "Ambiente: dev, staging, prod"
  type        = string
}

variable "vpc_id" {
  description = "ID de la VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block de la VPC"
  type        = string
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks de subnets privadas"
  type        = list(string)
}

variable "kms_enable_rotation" {
  description = "Habilitar rotación automática de claves KMS"
  type        = bool
  default     = true
}

variable "allowed_admin_cidrs" {
  description = "CIDR blocks permitidos para acceso administrativo"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
