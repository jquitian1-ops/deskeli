# ====================================================================
# Monitoring Module - CloudWatch Dashboards, Alarms, Insights
# ====================================================================
# Configura observabilidad completa del sistema TicketDesk

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ====================================================================
# CloudWatch Dashboard
# ====================================================================
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.environment}-ticketdesk"

  dashboard_body = jsonencode({
    widgets = [
      # ECS Service Health
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", { stat = "Average", label = "Avg CPU" }],
            [".", "MemoryUtilization", { stat = "Average", label = "Avg Memory" }],
            [".", "RunningCount", { stat = "Average", label = "Running Tasks" }],
            [".", "DesiredCount", { stat = "Average", label = "Desired Tasks" }]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "ECS Service Metrics"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },

      # ALB Metrics
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime"],
            [".", "RequestCount"],
            [".", "HealthyHostCount"],
            [".", "UnHealthyHostCount"]
          ]
          period = 300
          stat   = "Sum"
          region = data.aws_region.current.name
          title  = "ALB Performance"
        }
      },

      # RDS Database Health
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization"],
            [".", "DatabaseConnections"],
            [".", "FreeableMemory"],
            [".", "ReadLatency"]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "RDS Database Health"
        }
      },

      # Redis Cache
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ElastiCache", "EngineCPUUtilization"],
            [".", "DatabaseMemoryUsagePercentage"],
            [".", "Evictions"],
            [".", "NetworkBytesIn"]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "Redis Cache Metrics"
        }
      },

      # Application Logs Insights
      {
        type = "log"
        properties = {
          query   = "fields @timestamp, @message | stats count() as error_count by @message | sort error_count desc"
          region  = data.aws_region.current.name
          title   = "Recent Errors"
        }
      }
    ]
  })
}

# ====================================================================
# CloudWatch Alarms - ECS
# ====================================================================
resource "aws_cloudwatch_metric_alarm" "ecs_unhealthy_tasks" {
  alarm_name          = "${var.environment}-ecs-unhealthy-tasks"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "2"
  metric_name         = "RunningCount"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "Alerta cuando hay menos tasks de lo esperado"
  alarm_actions       = [var.sns_topic_arn]

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }
}

# ====================================================================
# CloudWatch Alarms - Database
# ====================================================================
resource "aws_cloudwatch_metric_alarm" "rds_read_latency" {
  alarm_name          = "${var.environment}-rds-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "ReadLatency"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = var.db_latency_threshold / 1000  # Convertir a segundos
  alarm_description   = "Alerta cuando latencia de lectura RDS > ${var.db_latency_threshold}ms"
  alarm_actions       = [var.sns_topic_arn]

  dimensions = {
    DBInstanceIdentifier = var.rds_db_instance_id
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_write_latency" {
  alarm_name          = "${var.environment}-rds-write-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "WriteLatency"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = var.db_latency_threshold / 1000
  alarm_description   = "Alerta cuando latencia de escritura RDS > ${var.db_latency_threshold}ms"
  alarm_actions       = [var.sns_topic_arn]

  dimensions = {
    DBInstanceIdentifier = var.rds_db_instance_id
  }
}

# ====================================================================
# CloudWatch Alarms - Application
# ====================================================================
resource "aws_cloudwatch_metric_alarm" "alb_http_4xx" {
  alarm_name          = "${var.environment}-alb-http-4xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HTTPCode_Target_4XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "100"
  alarm_description   = "Alerta por >100 errores 4XX en 5 minutos"
  alarm_actions       = [var.sns_topic_arn]

  dimensions = {
    LoadBalancer = data.aws_lb.main.arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_http_5xx" {
  alarm_name          = "${var.environment}-alb-http-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "60"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alerta por >10 errores 5XX en 1 minuto"
  alarm_actions       = [var.sns_topic_arn]

  dimensions = {
    LoadBalancer = data.aws_lb.main.arn_suffix
  }
}

# ====================================================================
# Log Group Insights Query Definitions
# ====================================================================
resource "aws_cloudwatch_query_definition" "error_rate" {
  name = "${var.environment}-error-rate"

  log_group_names = [
    "/ecs/${var.environment}-*"
  ]

  query_string = <<-EOQ
    fields @timestamp, @message, @logStream
    | filter @message like /ERROR|Exception|error/
    | stats count() as error_count, count()/pct(count(), 50) as error_rate by @logStream
  EOQ
}

resource "aws_cloudwatch_query_definition" "latency_p99" {
  name = "${var.environment}-latency-p99"

  log_group_names = [
    "/ecs/${var.environment}-*"
  ]

  query_string = <<-EOQ
    fields @duration
    | filter @duration > 0
    | stats pct(@duration, 99) as p99_latency,
            pct(@duration, 95) as p95_latency,
            pct(@duration, 50) as p50_latency
  EOQ
}

# ====================================================================
# Data Sources
# ====================================================================
data "aws_region" "current" {}

data "aws_lb" "main" {
  # Obtener ALB por target group
  load_balancer_arns = [
    "arn:aws:elasticache:${data.aws_region.current.name}:*:targetgroup/*"
  ]
}

# Nota: Data source ALB es aproximada. En producción, pasar target_group_arn desde main.tf
