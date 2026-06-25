# ====================================================================
# Security Module - IAM Roles, Security Groups, KMS, Secrets Manager
# ====================================================================
# Gestiona autenticación, encriptación y control de acceso

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ====================================================================
# KMS Key para encriptación en reposo
# ====================================================================
resource "aws_kms_key" "main" {
  description             = "KMS key para TicketDesk ${var.environment}"
  deletion_window_in_days = 10
  enable_key_rotation     = var.kms_enable_rotation

  tags = {
    Name = "${var.environment}-ticketdesk-key"
  }
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.environment}-ticketdesk"
  target_key_id = aws_kms_key.main.key_id
}

# ====================================================================
# ECS Task Execution Role
# ====================================================================
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.environment}-ecs-task-execution-role"

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
    Name = "${var.environment}-ecs-exec-role"
  }
}

# Política base para ECS Task Execution
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Política para acceder a Secrets Manager y CloudWatch Logs
resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "${var.environment}-ecs-execution-secrets"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.secret_key.arn,
          aws_secretsmanager_secret.db_credentials.arn,
          aws_secretsmanager_secret.anthropic_api_key.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = aws_kms_key.main.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:log-group:/ecs/*"
      }
    ]
  })
}

# ====================================================================
# ECS Task Role (permisos de la aplicación)
# ====================================================================
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.environment}-ecs-task-role"

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
    Name = "${var.environment}-ecs-task-role"
  }
}

# Permiso para acceder a S3 backups
resource "aws_iam_role_policy" "ecs_task_s3_access" {
  name = "${var.environment}-ecs-s3-access"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.environment}-ticketdesk-backups",
          "arn:aws:s3:::${var.environment}-ticketdesk-backups/*"
        ]
      }
    ]
  })
}

# Permiso para CloudWatch
resource "aws_iam_role_policy" "ecs_task_cloudwatch" {
  name = "${var.environment}-ecs-cloudwatch"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# ====================================================================
# RDS Enhanced Monitoring Role
# ====================================================================
resource "aws_iam_role" "rds_monitoring_role" {
  name = "${var.environment}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.environment}-rds-monitoring-role"
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring_policy" {
  role       = aws_iam_role.rds_monitoring_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# ====================================================================
# Security Groups
# ====================================================================

# App Security Group (ECS)
resource "aws_security_group" "app" {
  name        = "${var.environment}-ecs-app-sg"
  description = "Security group para ECS tasks de TicketDesk"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5050  # Flask port
    to_port         = 5050
    protocol        = "tcp"
    security_groups = []  # Será rellenado por ALB SG
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-app-sg"
  }
}

# Agregar ingreso desde ALB (evitar circular dependency)
resource "aws_security_group_rule" "app_from_alb" {
  type              = "ingress"
  from_port         = 5050
  to_port           = 5050
  protocol          = "tcp"
  security_group_id = aws_security_group.app.id
  source_security_group_id = null  # Será actualizado desde main.tf
  cidr_blocks       = var.private_subnet_cidrs

  description = "Tráfico desde ALB"
}

# DB Security Group (RDS)
resource "aws_security_group" "db" {
  name        = "${var.environment}-rds-db-sg"
  description = "Security group para RDS PostgreSQL"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.allowed_admin_cidrs
    description = "Admin access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-db-sg"
  }
}

# Cache Security Group (Redis)
resource "aws_security_group" "cache" {
  name        = "${var.environment}-redis-cache-sg"
  description = "Security group para ElastiCache Redis"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-cache-sg"
  }
}

# ====================================================================
# AWS Secrets Manager
# ====================================================================

# Secret: Flask SECRET_KEY
resource "aws_secretsmanager_secret" "secret_key" {
  name                    = "${var.environment}/ticketdesk/SECRET_KEY"
  description             = "Flask SECRET_KEY"
  recovery_window_in_days = 7
  kms_key_id              = aws_kms_key.main.id

  tags = {
    Name = "${var.environment}-secret-key"
  }
}

resource "aws_secretsmanager_secret_version" "secret_key" {
  secret_id = aws_secretsmanager_secret.secret_key.id
  secret_string = jsonencode({
    SECRET_KEY = random_password.secret_key.result
  })
}

# Secret: Database Credentials
resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${var.environment}/ticketdesk/DB_CREDENTIALS"
  description             = "PostgreSQL master credentials"
  recovery_window_in_days = 7
  kms_key_id              = aws_kms_key.main.id

  tags = {
    Name = "${var.environment}-db-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = "postgres"
    password = random_password.db_password.result
  })
}

# Secret: Anthropic API Key (placeholder)
resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name                    = "${var.environment}/ticketdesk/ANTHROPIC_API_KEY"
  description             = "Anthropic Claude API Key"
  recovery_window_in_days = 7
  kms_key_id              = aws_kms_key.main.id

  tags = {
    Name = "${var.environment}-anthropic-api-key"
  }
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = jsonencode({
    ANTHROPIC_API_KEY = "PLACEHOLDER_UPDATE_ME"
  })
}

# ====================================================================
# Random Passwords
# ====================================================================
resource "random_password" "secret_key" {
  length  = 32
  special = true
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# ====================================================================
# Data Sources
# ====================================================================
data "aws_caller_identity" "current" {}
