# ====================================================================
# Compute Module - Variables
# ====================================================================

variable "environment" {
  description = "Ambiente: dev, staging, prod"
  type        = string
}

variable "ecs_cluster_name" {
  description = "Nombre del cluster ECS"
  type        = string
}

variable "container_name" {
  description = "Nombre del contenedor"
  type        = string
}

variable "container_image" {
  description = "Image Docker para el contenedor"
  type        = string
}

variable "container_port" {
  description = "Puerto del contenedor"
  type        = number
}

variable "vpc_id" {
  description = "ID de la VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs de subnets privadas"
  type        = list(string)
}

variable "app_security_group_id" {
  description = "Security group para ECS"
  type        = string
}

variable "target_group_arn" {
  description = "ARN del target group del ALB"
  type        = string
}

variable "task_cpu" {
  description = "CPU para la task (256, 512, 1024, 2048, 4096)"
  type        = number
}

variable "task_memory" {
  description = "Memoria en MB"
  type        = number
}

variable "desired_count" {
  description = "Número deseado de tasks"
  type        = number
}

variable "min_capacity" {
  description = "Capacidad mínima para autoscaling"
  type        = number
}

variable "max_capacity" {
  description = "Capacidad máxima para autoscaling"
  type        = number
}

variable "environment_variables" {
  description = "Variables de entorno para el contenedor"
  type        = map(string)
}

variable "secrets" {
  description = "Secrets desde Secrets Manager (nombre -> ARN)"
  type        = map(string)
}

variable "iam_role_arn" {
  description = "ARN del rol IAM para ECS"
  type        = string
}

variable "cloudwatch_log_group" {
  description = "Nombre del log group CloudWatch"
  type        = string
}

variable "cloudwatch_log_retention" {
  description = "Días de retención de logs"
  type        = number
}
