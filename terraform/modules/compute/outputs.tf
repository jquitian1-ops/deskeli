# ====================================================================
# Compute Module - Outputs
# ====================================================================

output "ecs_cluster_id" {
  description = "ID del cluster ECS"
  value       = aws_ecs_cluster.main.id
}

output "ecs_cluster_name" {
  description = "Nombre del cluster ECS"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ARN del cluster ECS"
  value       = aws_ecs_cluster.main.arn
}

output "ecs_service_id" {
  description = "ID del servicio ECS"
  value       = aws_ecs_service.main.id
}

output "ecs_service_name" {
  description = "Nombre del servicio ECS"
  value       = aws_ecs_service.main.name
}

output "ecs_service_arn" {
  description = "ARN del servicio ECS"
  value       = aws_ecs_service.main.arn
}

output "task_definition_arn" {
  description = "ARN de la task definition"
  value       = aws_ecs_task_definition.main.arn
}

output "task_definition_revision" {
  description = "Revisión de la task definition"
  value       = aws_ecs_task_definition.main.revision
}

output "ecs_log_group_name" {
  description = "Nombre del log group CloudWatch"
  value       = aws_cloudwatch_log_group.ecs.name
}

output "autoscaling_target_id" {
  description = "ID del target de autoscaling"
  value       = aws_appautoscaling_target.ecs_target.id
}
