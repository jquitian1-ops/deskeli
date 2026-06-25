# ====================================================================
# Load Balancer Module - Variables
# ====================================================================

variable "environment" {
  description = "Ambiente: dev, staging, prod"
  type        = string
}

variable "vpc_id" {
  description = "ID de la VPC"
  type        = string
}

variable "public_subnet_ids" {
  description = "IDs de subnets públicas"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group para ALB"
  type        = string
}

variable "enable_https" {
  description = "Habilitar HTTPS"
  type        = bool
}

variable "certificate_arn" {
  description = "ARN del certificado ACM"
  type        = string
  default     = ""
  sensitive   = true
}

variable "app_port" {
  description = "Puerto de la aplicación"
  type        = number
}

variable "app_protocol" {
  description = "Protocolo de la aplicación (HTTP o HTTPS)"
  type        = string
  default     = "HTTP"
}

variable "health_check_path" {
  description = "Path para health check"
  type        = string
}

variable "health_check_timeout" {
  description = "Timeout para health check (segundos)"
  type        = number
}

variable "health_check_interval" {
  description = "Intervalo de health check (segundos)"
  type        = number
}

variable "healthy_threshold" {
  description = "Número de health checks exitosos antes de marcar healthy"
  type        = number
}

variable "unhealthy_threshold" {
  description = "Número de health checks fallidos antes de marcar unhealthy"
  type        = number
}
