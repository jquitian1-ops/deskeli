# ====================================================================
# Database Module - RDS PostgreSQL
# ====================================================================
# Configura instancia PostgreSQL con respaldos automáticos y monitoreo

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ====================================================================
# DB Parameter Group
# ====================================================================
resource "aws_db_parameter_group" "main" {
  family      = "postgres${replace(var.db_engine_version, "/\\..*$/", "")}"
  name        = "${var.environment}-ticketdesk-pg-params"
  description = "Custom parameter group for TicketDesk PostgreSQL"

  # Optimizaciones para PostgreSQL
  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_duration"
    value = "true"
  }

  parameter {
    name  = "log_lock_waits"
    value = "true"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # Log queries > 1s
  }

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  parameter {
    name  = "max_connections"
    value = "200"
  }

  parameter {
    name  = "max_prepared_transactions"
    value = "100"
  }

  # Replication settings (para standbys)
  parameter {
    name  = "wal_level"
    value = "replica"
  }

  parameter {
    name  = "max_wal_senders"
    value = "10"
  }

  tags = {
    Name = "${var.environment}-pg-params"
  }
}

# ====================================================================
# RDS Subnet Group
# ====================================================================
resource "aws_db_subnet_group" "main" {
  name       = "${var.environment}-ticketdesk-db-subnet"
  subnet_ids = var.db_subnet_group_name  # Este es el recurso creado en main.tf

  # Alternativamente, si se pasa lista:
  # subnet_ids = var.subnet_ids

  tags = {
    Name = "${var.environment}-db-subnet-group"
  }
}

# ====================================================================
# RDS PostgreSQL Instance
# ====================================================================
resource "aws_db_instance" "main" {
  identifier              = "${var.environment}-ticketdesk-db"
  engine                  = "postgres"
  engine_version          = var.db_engine_version
  instance_class          = var.db_instance_class
  allocated_storage       = var.db_allocated_storage
  storage_type            = "gp3"
  iops                    = 3000
  storage_encrypted       = true
  kms_key_id              = var.kms_key_id

  # Database
  db_name  = "ticketdesk"
  username = "postgres"
  password = random_password.db_master_password.result
  port     = 5432

  # Network & Security
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.db_security_group_id]
  publicly_accessible    = var.publicly_accessible

  # Availability & Backups
  multi_az                    = var.multi_az
  backup_retention_period     = var.db_backup_retention_days
  backup_window               = var.db_backup_window
  maintenance_window          = var.db_maintenance_window
  copy_tags_to_snapshot       = true
  delete_automated_backups    = false  # Mantener backups al eliminar DB
  skip_final_snapshot         = false
  final_snapshot_identifier   = "${var.environment}-ticketdesk-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  # Monitoreo
  enabled_cloudwatch_logs_exports = ["postgresql"]
  monitoring_interval              = var.monitoring_interval
  monitoring_role_arn              = var.monitoring_role_arn
  enable_performance_insights      = var.enable_performance_insights
  performance_insights_retention_period = var.enable_performance_insights ? 7 : null

  # Parameters & Options
  parameter_group_name = aws_db_parameter_group.main.name
  option_group_name    = aws_db_option_group.main.name

  # Upgrades
  auto_minor_version_upgrade = true
  apply_immediately          = false

  # Deletion protection
  deletion_protection = var.environment == "prod" ? true : false

  tags = {
    Name = "${var.environment}-ticketdesk-db"
  }

  depends_on = [aws_db_parameter_group.main]
}

# ====================================================================
# DB Option Group
# ====================================================================
resource "aws_db_option_group" "main" {
  name                     = "${var.environment}-ticketdesk-pg-options"
  option_group_description = "Option group for TicketDesk PostgreSQL"
  engine_name              = "postgres"
  major_engine_version     = replace(var.db_engine_version, "/\\..*$/", "")

  tags = {
    Name = "${var.environment}-pg-options"
  }
}

# ====================================================================
# RDS Enhanced Monitoring (via SNS topic)
# ====================================================================
resource "aws_sns_topic" "rds_alerts" {
  name              = "${var.environment}-rds-alerts"
  kms_master_key_id = var.kms_key_id

  tags = {
    Name = "${var.environment}-rds-alerts"
  }
}

# ====================================================================
# CloudWatch Alarms for RDS
# ====================================================================
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${var.environment}-rds-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "Alerta cuando CPU de RDS > 80%"
  alarm_actions       = [aws_sns_topic.rds_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_storage" {
  alarm_name          = "${var.environment}-rds-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "10737418240"  # 10 GB
  alarm_description   = "Alerta cuando almacenamiento libre < 10 GB"
  alarm_actions       = [aws_sns_topic.rds_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "${var.environment}-rds-high-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "150"
  alarm_description   = "Alerta cuando conexiones activas > 150"
  alarm_actions       = [aws_sns_topic.rds_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
}

# ====================================================================
# Random Password for RDS Master
# ====================================================================
resource "random_password" "db_master_password" {
  length  = 32
  special = true
}

# ====================================================================
# Data Sources
# ====================================================================
data "aws_db_instance" "main" {
  db_instance_identifier = aws_db_instance.main.id
  depends_on             = [aws_db_instance.main]
}
