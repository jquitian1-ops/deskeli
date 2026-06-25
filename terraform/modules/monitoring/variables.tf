# ====================================================================
# Monitoring Module - Variables
# ====================================================================

variable "environment" {
  description = "Ambiente: dev, staging, prod"
  type        = string
}

variable "ecs_cluster_name" {
  description = "Nombre del cluster ECS"
  type        = string
}

variable "ecs_service_name" {
  description = "Nombre del servicio ECS"
  type        = string
}

variable "rds_db_instance_id" {
  description = "ID de la instancia RDS"
  type        = string
}

variable "alb_target_group_arn" {
  description = "ARN del target group ALB"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN del SNS topic para alertas"
  type        = string
}

variable "cpu_threshold" {
  description = "Umbral de CPU para alerta (%)"
  type        = number
}

variable "memory_threshold" {
  description = "Umbral de memoria para alerta (%)"
  type        = number
}

variable "db_latency_threshold" {
  description = "Umbral de latencia DB (ms)"
  type        = number
}

variable "cloudwatch_log_retention" {
  description = "Días de retención de logs"
  type        = number
}

variable "enable_performance_insights" {
  description = "Habilitar Performance Insights"
  type        = bool
}
