# ====================================================================
# Database Module - Outputs
# ====================================================================

output "db_endpoint" {
  description = "RDS endpoint (host:port)"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "db_instance_id" {
  description = "ID de la instancia RDS"
  value       = aws_db_instance.main.id
}

output "db_name" {
  description = "Nombre de la base de datos"
  value       = aws_db_instance.main.db_name
}

output "db_port" {
  description = "Puerto de RDS"
  value       = aws_db_instance.main.port
}

output "db_master_username" {
  description = "Usuario master de RDS"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "db_resource_id" {
  description = "Resource ID para enhanced monitoring"
  value       = aws_db_instance.main.resource_id
}

output "db_arn" {
  description = "ARN de la instancia RDS"
  value       = aws_db_instance.main.arn
}

output "multi_az_enabled" {
  description = "¿Multi-AZ está habilitado?"
  value       = aws_db_instance.main.multi_az
}

output "backup_retention_days" {
  description = "Días de retención de backups"
  value       = aws_db_instance.main.backup_retention_period
}

output "parameter_group_id" {
  description = "ID del parameter group"
  value       = aws_db_parameter_group.main.id
}

output "subnet_group_id" {
  description = "ID del subnet group"
  value       = aws_db_subnet_group.main.id
}

output "rds_alerts_topic_arn" {
  description = "ARN del SNS topic para alertas RDS"
  value       = aws_sns_topic.rds_alerts.arn
}
