# ========================================================================
# TicketDesk LocalStack Infrastructure
# ========================================================================

# ========================================================================
# 1. VPC & Networking
# ========================================================================

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "ticketdesk-vpc"
  }
}

resource "aws_subnet" "main" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.subnet_cidr
  availability_zone = "${var.aws_region}a"

  tags = {
    Name = "ticketdesk-subnet"
  }
}

resource "aws_security_group" "main" {
  name        = "ticketdesk-sg"
  description = "Security group for TicketDesk application"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "ticketdesk-sg"
  }
}

# Ingress rules
resource "aws_vpc_security_group_ingress_rule" "app" {
  security_group_id = aws_security_group.main.id

  from_port   = 5050
  to_port     = 5050
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "ticketdesk-app"
  }
}

resource "aws_vpc_security_group_ingress_rule" "postgres" {
  security_group_id = aws_security_group.main.id

  from_port   = 5432
  to_port     = 5432
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "postgres"
  }
}

resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.main.id

  from_port   = 80
  to_port     = 80
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "http"
  }
}

resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = aws_security_group.main.id

  from_port   = 443
  to_port     = 443
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "https"
  }
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.main.id

  from_port   = 0
  to_port     = 0
  ip_protocol = "-1"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "allow-all-outbound"
  }
}

# ========================================================================
# 2. S3 Buckets
# ========================================================================

resource "aws_s3_bucket" "backups" {
  bucket = "ticketdesk-backups-${var.environment}"

  tags = {
    Name = "TicketDesk Backups"
  }
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket" "uploads" {
  bucket = "ticketdesk-uploads-${var.environment}"

  tags = {
    Name = "TicketDesk Uploads"
  }
}

resource "aws_s3_bucket" "logs" {
  bucket = "ticketdesk-logs-${var.environment}"

  tags = {
    Name = "TicketDesk Logs"
  }
}

# ========================================================================
# 3. RDS (PostgreSQL)
# ========================================================================

resource "aws_db_instance" "postgres" {
  identifier     = "ticketdesk-db"
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = "db.t3.micro"

  db_name  = "ticketdesk"
  username = var.db_username
  password = var.db_password

  allocated_storage = 20
  storage_type      = "gp2"
  storage_encrypted = true

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"

  skip_final_snapshot       = true
  publicly_accessible       = true

  vpc_security_group_ids = [aws_security_group.main.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  multi_az = false
  deletion_protection = false

  tags = {
    Name = "TicketDesk Database"
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "ticketdesk-subnet-group"
  subnet_ids = [aws_subnet.main.id]

  tags = {
    Name = "TicketDesk Subnet Group"
  }
}

# ========================================================================
# 4. Secrets Manager
# ========================================================================

resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "ticketdesk/db-credentials"
  recovery_window_in_days = 7

  tags = {
    Name = "Database Credentials"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
    host     = aws_db_instance.postgres.address
    port     = aws_db_instance.postgres.port
    dbname   = aws_db_instance.postgres.db_name
  })
}

resource "aws_secretsmanager_secret" "api_keys" {
  name                    = "ticketdesk/api-keys"
  recovery_window_in_days = 7

  tags = {
    Name = "API Keys"
  }
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id
  secret_string = jsonencode({
    anthropic_api_key = var.anthropic_api_key
    teams_webhook_url = var.teams_webhook_url
  })
}

# ========================================================================
# 5. CloudWatch Monitoring
# ========================================================================

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ticketdesk/app"
  retention_in_days = 7

  tags = {
    Name = "TicketDesk App Logs"
  }
}

resource "aws_cloudwatch_log_group" "rds" {
  name              = "/ticketdesk/rds"
  retention_in_days = 7

  tags = {
    Name = "TicketDesk RDS Logs"
  }
}

resource "aws_cloudwatch_metric_alarm" "db_cpu" {
  alarm_name          = "ticketdesk-db-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres.id
  }

  alarm_description = "Alert when RDS CPU exceeds 80%"
  alarm_actions     = [aws_sns_topic.alerts.arn]

  tags = {
    Name = "Database CPU Alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "db_connections" {
  alarm_name          = "ticketdesk-db-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 100

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.postgres.id
  }

  alarm_description = "Alert when connections exceed 100"
  alarm_actions     = [aws_sns_topic.alerts.arn]

  tags = {
    Name = "Database Connections Alarm"
  }
}

# ========================================================================
# 6. SNS (Notifications)
# ========================================================================

resource "aws_sns_topic" "notifications" {
  name = "ticketdesk-notifications"

  tags = {
    Name = "TicketDesk Notifications"
  }
}

resource "aws_sns_topic" "alerts" {
  name = "ticketdesk-alerts"

  tags = {
    Name = "TicketDesk Alerts"
  }
}

# ========================================================================
# 7. SQS (Message Queue)
# ========================================================================

resource "aws_sqs_queue" "tasks" {
  name                      = "ticketdesk-tasks"
  visibility_timeout_seconds = 300
  message_retention_seconds = 1209600  # 14 days
  receive_wait_time_seconds = 20

  tags = {
    Name = "TicketDesk Task Queue"
  }
}

resource "aws_sqs_queue_policy" "tasks" {
  queue_url = aws_sqs_queue.tasks.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.tasks.arn
      }
    ]
  })
}

# ========================================================================
# 8. ECS Cluster (Optional - for containerized deployments)
# ========================================================================

resource "aws_ecs_cluster" "main" {
  name = "ticketdesk-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "TicketDesk ECS Cluster"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

# ========================================================================
# 9. IAM Roles
# ========================================================================

resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ticketdesk-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "ECS Task Execution Role"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_task_role_policy" {
  name = "ticketdesk-ecs-task-policy"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.backups.arn}/*",
          "${aws_s3_bucket.uploads.arn}/*",
          "${aws_s3_bucket.logs.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.db_credentials.arn,
          aws_secretsmanager_secret.api_keys.arn
        ]
      }
    ]
  })
}

# ========================================================================
# 10. Outputs
# ========================================================================

output "vpc_id" {
  description = "ID de la VPC creada"
  value       = aws_vpc.main.id
}

output "subnet_id" {
  description = "ID de la subnet"
  value       = aws_subnet.main.id
}

output "security_group_id" {
  description = "ID del security group"
  value       = aws_security_group.main.id
}

output "rds_endpoint" {
  description = "RDS Database Endpoint"
  value       = aws_db_instance.postgres.endpoint
}

output "rds_address" {
  description = "RDS Database Address"
  value       = aws_db_instance.postgres.address
}

output "rds_port" {
  description = "RDS Database Port"
  value       = aws_db_instance.postgres.port
}

output "s3_backup_bucket" {
  description = "S3 bucket para backups"
  value       = aws_s3_bucket.backups.id
}

output "s3_uploads_bucket" {
  description = "S3 bucket para uploads"
  value       = aws_s3_bucket.uploads.id
}

output "s3_logs_bucket" {
  description = "S3 bucket para logs"
  value       = aws_s3_bucket.logs.id
}

output "sqs_queue_url" {
  description = "SQS Queue URL"
  value       = aws_sqs_queue.tasks.url
}

output "sqs_queue_arn" {
  description = "SQS Queue ARN"
  value       = aws_sqs_queue.tasks.arn
}

output "sns_notifications_topic_arn" {
  description = "SNS Notifications Topic ARN"
  value       = aws_sns_topic.notifications.arn
}

output "sns_alerts_topic_arn" {
  description = "SNS Alerts Topic ARN"
  value       = aws_sns_topic.alerts.arn
}

output "ecs_cluster_name" {
  description = "ECS Cluster Name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ECS Cluster ARN"
  value       = aws_ecs_cluster.main.arn
}

output "cloudwatch_log_group_app" {
  description = "CloudWatch Log Group para la aplicación"
  value       = aws_cloudwatch_log_group.app.name
}

output "cloudwatch_log_group_rds" {
  description = "CloudWatch Log Group para RDS"
  value       = aws_cloudwatch_log_group.rds.name
}
