# ====================================================================
# Cache Module - ElastiCache Redis
# ====================================================================
# Configura cluster Redis para sesiones y JWT blacklist

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ====================================================================
# ElastiCache Subnet Group
# ====================================================================
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.environment}-ticketdesk-redis-subnet"
  subnet_ids = var.subnet_ids

  tags = {
    Name = "${var.environment}-redis-subnet-group"
  }
}

# ====================================================================
# ElastiCache Parameter Group
# ====================================================================
resource "aws_elasticache_parameter_group" "main" {
  family      = "redis7"
  name        = "${var.environment}-ticketdesk-redis-params"
  description = "Custom parameter group for TicketDesk Redis"

  # Configuración para JWT blacklist y sesiones
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"  # Evictar keys menos usadas
  }

  parameter {
    name  = "timeout"
    value = "300"  # 5 min connection timeout
  }

  parameter {
    name  = "tcp-keepalive"
    value = "60"
  }

  tags = {
    Name = "${var.environment}-redis-params"
  }
}

# ====================================================================
# ElastiCache Redis Cluster
# ====================================================================
resource "aws_elasticache_replication_group" "main" {
  replication_group_description = "Redis cluster para TicketDesk ${var.environment}"
  engine                         = "redis"
  engine_version                 = "7.0"
  node_type                      = var.redis_node_type
  num_cache_clusters             = var.redis_num_cache_nodes
  automatic_failover_enabled     = var.redis_automatic_failover
  multi_az_enabled               = var.redis_automatic_failover

  port                      = 6379
  parameter_group_name      = aws_elasticache_parameter_group.main.name
  subnet_group_name         = aws_elasticache_subnet_group.main.name
  security_group_ids        = [var.cache_security_group_id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = false  # Cambiar a true en prod si requiere mTLS

  # Backups automáticos
  snapshot_retention_limit = var.redis_snapshot_retention_days
  snapshot_window          = "03:00-04:00"

  # Logs
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
    enabled          = true
  }

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_engine_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
    enabled          = true
  }

  # Notifications
  notification_topic_arn = aws_sns_topic.redis_alerts.arn

  tags = {
    Name = "${var.environment}-ticketdesk-redis"
  }

  depends_on = [aws_elasticache_subnet_group.main, aws_elasticache_parameter_group.main]
}

# ====================================================================
# CloudWatch Log Groups
# ====================================================================
resource "aws_cloudwatch_log_group" "redis_slow_log" {
  name              = "/aws/elasticache/${var.environment}/redis/slow-log"
  retention_in_days = 30

  tags = {
    Name = "${var.environment}-redis-slow-log"
  }
}

resource "aws_cloudwatch_log_group" "redis_engine_log" {
  name              = "/aws/elasticache/${var.environment}/redis/engine-log"
  retention_in_days = 30

  tags = {
    Name = "${var.environment}-redis-engine-log"
  }
}

# ====================================================================
# SNS Topic para alertas Redis
# ====================================================================
resource "aws_sns_topic" "redis_alerts" {
  name              = "${var.environment}-redis-alerts"
  kms_master_key_id = var.kms_key_id

  tags = {
    Name = "${var.environment}-redis-alerts"
  }
}

# ====================================================================
# CloudWatch Alarms para Redis
# ====================================================================
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${var.environment}-redis-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "EngineCPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "Alerta cuando CPU de Redis > 75%"
  alarm_actions       = [aws_sns_topic.redis_alerts.arn]

  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.main.id
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  alarm_name          = "${var.environment}-redis-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "Alerta cuando memoria de Redis > 80%"
  alarm_actions       = [aws_sns_topic.redis_alerts.arn]

  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.main.id
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_evictions" {
  alarm_name          = "${var.environment}-redis-evictions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Sum"
  threshold           = "100"
  alarm_description   = "Alerta cuando hay evictions en Redis (memoria agotada)"
  alarm_actions       = [aws_sns_topic.redis_alerts.arn]

  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.main.id
  }
}
