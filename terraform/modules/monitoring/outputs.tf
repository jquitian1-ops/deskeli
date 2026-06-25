# ====================================================================
# Monitoring Module - Outputs
# ====================================================================

output "dashboard_url" {
  description = "URL del CloudWatch Dashboard"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${var.environment}-ticketdesk"
}

output "ecs_log_group_name" {
  description = "Nombre del log group ECS"
  value       = "/ecs/${var.environment}-ticketdesk-app"
}

output "error_rate_query_id" {
  description = "ID de la query definition para error rate"
  value       = aws_cloudwatch_query_definition.error_rate.id
}

output "latency_p99_query_id" {
  description = "ID de la query definition para latencia P99"
  value       = aws_cloudwatch_query_definition.latency_p99.id
}

data "aws_region" "current" {}
