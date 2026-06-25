# ====================================================================
# TicketDesk Enterprise - Output Values
# ====================================================================
# Valores útiles para consumir por otros stacks o dashboards

# ====================================================================
# VPC & Networking Outputs
# ====================================================================
output "vpc_id" {
  description = "ID de la VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "CIDR block de la VPC"
  value       = module.vpc.vpc_cidr
}

output "public_subnet_ids" {
  description = "IDs de subnets públicas"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs de subnets privadas"
  value       = module.vpc.private_subnet_ids
}

output "nat_gateway_ip" {
  description = "IP Elástica del NAT Gateway"
  value       = module.vpc.nat_gateway_ip
}

# ====================================================================
# Load Balancer Outputs
# ====================================================================
output "alb_dns_name" {
  description = "DNS del Application Load Balancer"
  value       = module.lb.alb_dns_name
}

output "alb_arn" {
  description = "ARN del Application Load Balancer"
  value       = module.lb.alb_arn
}

output "alb_zone_id" {
  description = "Hosted Zone ID del ALB (para registros Route53)"
  value       = module.lb.alb_zone_id
}

output "target_group_arn" {
  description = "ARN del Target Group ECS"
  value       = module.lb.target_group_arn
}

# ====================================================================
# ECS Compute Outputs
# ====================================================================
output "ecs_cluster_name" {
  description = "Nombre del cluster ECS"
  value       = module.compute.ecs_cluster_name
}

output "ecs_cluster_arn" {
  description = "ARN del cluster ECS"
  value       = module.compute.ecs_cluster_arn
}

output "ecs_service_name" {
  description = "Nombre del servicio ECS"
  value       = module.compute.ecs_service_name
}

output "ecs_service_arn" {
  description = "ARN del servicio ECS"
  value       = module.compute.ecs_service_arn
}

output "ecs_task_definition_arn" {
  description = "ARN de la Task Definition"
  value       = module.compute.task_definition_arn
}

output "ecs_task_execution_role_arn" {
  description = "ARN del rol de ejecución ECS"
  value       = module.security.ecs_task_execution_role_arn
}

# ====================================================================
# Database Outputs
# ====================================================================
output "db_endpoint" {
  description = "Endpoint de RDS PostgreSQL (host:port)"
  value       = module.database.db_endpoint
  sensitive   = true
}

output "db_instance_id" {
  description = "ID de la instancia RDS"
  value       = module.database.db_instance_id
}

output "db_name" {
  description = "Nombre de la base de datos"
  value       = module.database.db_name
}

output "db_port" {
  description = "Puerto de RDS"
  value       = module.database.db_port
}

output "db_master_username" {
  description = "Usuario master de RDS"
  value       = module.database.db_master_username
  sensitive   = true
}

output "db_resource_id" {
  description = "Resource ID para enhanced monitoring"
  value       = module.database.db_resource_id
}

output "db_multi_az" {
  description = "¿Multi-AZ habilitado?"
  value       = module.database.multi_az_enabled
}

# ====================================================================
# Cache Outputs
# ====================================================================
output "redis_endpoint" {
  description = "Endpoint del cluster Redis (host:port)"
  value       = module.cache.redis_endpoint
  sensitive   = true
}

output "redis_cluster_id" {
  description = "ID del cluster Redis"
  value       = module.cache.cluster_id
}

output "redis_engine_version" {
  description = "Versión de Redis"
  value       = module.cache.engine_version
}

output "redis_node_type" {
  description = "Tipo de nodo Redis"
  value       = module.cache.node_type
}

# ====================================================================
# Storage Outputs
# ====================================================================
output "backup_bucket_name" {
  description = "Nombre del bucket S3 para backups"
  value       = module.storage.backup_bucket_name
}

output "backup_bucket_arn" {
  description = "ARN del bucket S3"
  value       = module.storage.backup_bucket_arn
}

output "backup_bucket_domain_name" {
  description = "Domain name del bucket S3"
  value       = module.storage.backup_bucket_domain_name
}

output "backup_bucket_region" {
  description = "Región del bucket S3"
  value       = module.storage.backup_bucket_region
}

# ====================================================================
# Security Outputs
# ====================================================================
output "kms_key_id" {
  description = "ID de la clave KMS maestra"
  value       = module.security.kms_key_id
  sensitive   = true
}

output "kms_key_arn" {
  description = "ARN de la clave KMS"
  value       = module.security.kms_key_arn
  sensitive   = true
}

output "app_security_group_id" {
  description = "Security group de aplicación ECS"
  value       = module.security.app_security_group_id
}

output "db_security_group_id" {
  description = "Security group de RDS"
  value       = module.security.db_security_group_id
}

output "cache_security_group_id" {
  description = "Security group de Redis"
  value       = module.security.cache_security_group_id
}

output "alb_security_group_id" {
  description = "Security group del ALB"
  value       = aws_security_group.alb.id
}

# ====================================================================
# Monitoring Outputs
# ====================================================================
output "cloudwatch_log_group" {
  description = "Log group de CloudWatch para ECS"
  value       = module.monitoring.ecs_log_group_name
}

output "sns_alert_topic_arn" {
  description = "ARN del topic SNS para alertas"
  value       = aws_sns_topic.alerts.arn
}

output "dashboard_url" {
  description = "URL del dashboard CloudWatch"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${var.environment}-ticketdesk"
}

# ====================================================================
# Connection Strings (para variables de entorno de la app)
# ====================================================================
output "database_connection_string" {
  description = "Connection string PostgreSQL (completa, para .env)"
  value       = "postgresql://postgres:PASSWORD@${module.database.db_endpoint}/${module.database.db_name}"
  sensitive   = true
}

output "redis_connection_string" {
  description = "Connection string Redis (para .env)"
  value       = "redis://${module.cache.redis_endpoint}"
  sensitive   = true
}

# ====================================================================
# Deployment Info
# ====================================================================
output "environment" {
  description = "Ambiente desplegado"
  value       = var.environment
}

output "aws_region" {
  description = "Región AWS"
  value       = var.aws_region
}

output "deployment_timestamp" {
  description = "Timestamp de despliegue"
  value       = timestamp()
}

output "terraform_version" {
  description = "Versión de Terraform requerida"
  value       = "~> 1.0"
}

# ====================================================================
# CDN Output (si está habilitado)
# ====================================================================
output "cloudfront_distribution_id" {
  description = "ID de CloudFront distribution"
  value       = try(aws_cloudfront_distribution.cdn[0].id, null)
}

output "cloudfront_domain_name" {
  description = "Domain name de CloudFront"
  value       = try(aws_cloudfront_distribution.cdn[0].domain_name, null)
}

# ====================================================================
# Acceso a Recursos (Console Links)
# ====================================================================
output "aws_console_links" {
  description = "Links útiles a AWS Console"
  value = {
    vpc = "https://console.aws.amazon.com/vpc/home?region=${var.aws_region}"
    rds = "https://console.aws.amazon.com/rds/home?region=${var.aws_region}"
    ecs = "https://console.aws.amazon.com/ecs/v2/clusters/${module.compute.ecs_cluster_name}?region=${var.aws_region}"
    s3  = "https://s3.console.aws.amazon.com/s3/buckets/${module.storage.backup_bucket_name}?region=${var.aws_region}"
    logs = "https://console.aws.amazon.com/logs/home?region=${var.aws_region}#logStream:group=${module.monitoring.ecs_log_group_name}"
  }
}

# ====================================================================
# Health Check URLs
# ====================================================================
output "health_check_urls" {
  description = "URLs para verificar salud de la aplicación"
  value = {
    alb_health = "http://${module.lb.alb_dns_name}/api/health"
    alb_metrics = "http://${module.lb.alb_dns_name}/api/metrics"
  }
}
