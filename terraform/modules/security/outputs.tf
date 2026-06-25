# ====================================================================
# Security Module - Outputs
# ====================================================================

output "kms_key_id" {
  description = "ID de la clave KMS"
  value       = aws_kms_key.main.key_id
  sensitive   = true
}

output "kms_key_arn" {
  description = "ARN de la clave KMS"
  value       = aws_kms_key.main.arn
  sensitive   = true
}

output "app_security_group_id" {
  description = "Security group ID para ECS tasks"
  value       = aws_security_group.app.id
}

output "db_security_group_id" {
  description = "Security group ID para RDS"
  value       = aws_security_group.db.id
}

output "cache_security_group_id" {
  description = "Security group ID para Redis"
  value       = aws_security_group.cache.id
}

output "ecs_task_execution_role_arn" {
  description = "ARN del rol de ejecución ECS"
  value       = aws_iam_role.ecs_task_execution_role.arn
}

output "ecs_task_role_arn" {
  description = "ARN del rol de tarea ECS"
  value       = aws_iam_role.ecs_task_role.arn
}

output "rds_monitoring_role_arn" {
  description = "ARN del rol de monitoring RDS"
  value       = aws_iam_role.rds_monitoring_role.arn
}

output "secret_key_arn" {
  description = "ARN del secret Flask SECRET_KEY"
  value       = aws_secretsmanager_secret.secret_key.arn
  sensitive   = true
}

output "db_credentials_arn" {
  description = "ARN del secret de credenciales DB"
  value       = aws_secretsmanager_secret.db_credentials.arn
  sensitive   = true
}

output "anthropic_api_key_arn" {
  description = "ARN del secret Anthropic API Key"
  value       = aws_secretsmanager_secret.anthropic_api_key.arn
  sensitive   = true
}

output "db_master_password" {
  description = "Password generada para RDS master"
  value       = random_password.db_password.result
  sensitive   = true
}
