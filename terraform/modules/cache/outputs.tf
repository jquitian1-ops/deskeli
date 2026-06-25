# ====================================================================
# Cache Module - Outputs
# ====================================================================

output "redis_endpoint" {
  description = "Redis cluster endpoint (host:port)"
  value       = "${aws_elasticache_replication_group.main.primary_endpoint_address}:6379"
  sensitive   = true
}

output "redis_address" {
  description = "Redis primary endpoint address"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
  sensitive   = true
}

output "redis_port" {
  description = "Redis port"
  value       = 6379
}

output "cluster_id" {
  description = "ID del replication group"
  value       = aws_elasticache_replication_group.main.id
}

output "cluster_arn" {
  description = "ARN del replication group"
  value       = aws_elasticache_replication_group.main.arn
}

output "engine_version" {
  description = "Versión de Redis"
  value       = aws_elasticache_replication_group.main.engine_version
}

output "node_type" {
  description = "Tipo de nodo Redis"
  value       = aws_elasticache_replication_group.main.node_type
}

output "num_cache_clusters" {
  description = "Número de nodos"
  value       = aws_elasticache_replication_group.main.num_cache_clusters
}

output "parameter_group_name" {
  description = "Nombre del parameter group"
  value       = aws_elasticache_parameter_group.main.name
}

output "subnet_group_name" {
  description = "Nombre del subnet group"
  value       = aws_elasticache_subnet_group.main.name
}

output "redis_alerts_topic_arn" {
  description = "ARN del SNS topic para alertas"
  value       = aws_sns_topic.redis_alerts.arn
}
