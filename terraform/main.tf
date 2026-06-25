# ====================================================================
# TicketDesk Enterprise - Terraform Root Module
# ====================================================================
# Configuración principal que orquesta todos los módulos
# Soporta 8,000 empleados con 100 técnicos IT
# Stack: Flask + PostgreSQL + Redis + ECS Fargate + ALB

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Descomentar para backend remoto (S3 + DynamoDB)
  # backend "s3" {
  #   bucket         = "ticketdesk-terraform-state"
  #   key            = "prod/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "TicketDesk"
      Environment = var.environment
      ManagedBy   = "Terraform"
      CreatedAt   = timestamp()
    }
  }
}

# ====================================================================
# VPC Module - Networking Infrastructure
# ====================================================================
module "vpc" {
  source = "./modules/vpc"

  environment            = var.environment
  vpc_cidr               = var.vpc_cidr
  availability_zones     = var.availability_zones
  public_subnet_cidrs    = var.public_subnet_cidrs
  private_subnet_cidrs   = var.private_subnet_cidrs
  enable_nat_gateway     = var.enable_nat_gateway
  enable_flow_logs       = var.enable_flow_logs
}

# ====================================================================
# Security Module - IAM, Security Groups, KMS
# ====================================================================
module "security" {
  source = "./modules/security"

  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  vpc_cidr              = var.vpc_cidr
  private_subnet_cidrs  = var.private_subnet_cidrs
  kms_enable_rotation   = var.kms_enable_rotation
  allowed_admin_cidrs   = var.allowed_admin_cidrs
}

# ====================================================================
# Database Module - RDS PostgreSQL
# ====================================================================
module "database" {
  source = "./modules/database"

  environment                = var.environment
  db_instance_class          = var.db_instance_class
  db_allocated_storage       = var.db_allocated_storage
  db_engine_version          = var.db_engine_version
  db_backup_retention_days   = var.db_backup_retention_days
  db_backup_window           = var.db_backup_window
  db_maintenance_window      = var.db_maintenance_window
  multi_az                   = var.multi_az
  publicly_accessible        = var.db_publicly_accessible
  vpc_id                     = module.vpc.vpc_id
  db_subnet_group_name       = aws_db_subnet_group.main.name
  db_security_group_id       = module.security.db_security_group_id
  kms_key_id                 = module.security.kms_key_id

  depends_on = [aws_db_subnet_group.main]
}

# DB Subnet Group (Requerido para RDS)
resource "aws_db_subnet_group" "main" {
  name       = "${var.environment}-ticketdesk-db-subnet-group"
  subnet_ids = module.vpc.private_subnet_ids

  tags = {
    Name = "${var.environment}-db-subnet-group"
  }
}

# ====================================================================
# Cache Module - ElastiCache Redis (para sesiones + JWT blacklist)
# ====================================================================
module "cache" {
  source = "./modules/cache"

  environment                    = var.environment
  redis_node_type               = var.redis_node_type
  redis_num_cache_nodes         = var.redis_num_cache_nodes
  redis_automatic_failover      = var.redis_automatic_failover
  redis_automatic_backup        = var.redis_automatic_backup
  redis_snapshot_retention_days = var.redis_snapshot_retention_days
  vpc_id                        = module.vpc.vpc_id
  subnet_ids                    = module.vpc.private_subnet_ids
  cache_security_group_id       = module.security.cache_security_group_id
  kms_key_id                    = module.security.kms_key_id

  depends_on = [module.vpc]
}

# ====================================================================
# Storage Module - S3 para backups y assets
# ====================================================================
module "storage" {
  source = "./modules/storage"

  environment                 = var.environment
  backup_retention_days       = var.backup_retention_days
  enable_versioning           = var.enable_versioning
  enable_encryption           = var.enable_encryption
  kms_key_id                  = module.security.kms_key_id
  enable_lifecycle_policy     = var.enable_lifecycle_policy
  mfa_delete_required         = var.mfa_delete_required
}

# ====================================================================
# Security Group para ALB (Load Balancer)
# ====================================================================
resource "aws_security_group" "alb" {
  name        = "${var.environment}-ticketdesk-alb"
  description = "Security group for ALB"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-alb-sg"
  }
}

# ====================================================================
# Load Balancer Module
# ====================================================================
module "lb" {
  source = "./modules/lb"

  environment              = var.environment
  vpc_id                   = module.vpc.vpc_id
  public_subnet_ids        = module.vpc.public_subnet_ids
  alb_security_group_id    = aws_security_group.alb.id
  enable_https             = var.enable_https
  certificate_arn          = var.acm_certificate_arn
  app_port                 = var.app_port
  app_protocol             = "HTTP"
  health_check_path        = "/api/health"
  health_check_timeout     = 5
  health_check_interval    = 30
  healthy_threshold        = 2
  unhealthy_threshold      = 3
}

# ====================================================================
# Compute Module - ECS Fargate Cluster
# ====================================================================
module "compute" {
  source = "./modules/compute"

  environment              = var.environment
  ecs_cluster_name         = "ticketdesk-${var.environment}"
  container_name           = "ticketdesk-app"
  container_image          = var.container_image
  container_port           = var.app_port
  vpc_id                   = module.vpc.vpc_id
  private_subnet_ids       = module.vpc.private_subnet_ids
  app_security_group_id    = module.security.app_security_group_id
  target_group_arn         = module.lb.target_group_arn
  task_cpu                 = var.task_cpu
  task_memory              = var.task_memory
  desired_count            = var.ecs_desired_count
  min_capacity             = var.ecs_min_capacity
  max_capacity             = var.ecs_max_capacity

  # Environment variables
  environment_variables = {
    FLASK_ENV               = var.environment
    DATABASE_URL            = "postgresql://${module.database.db_endpoint}:5432/${module.database.db_name}"
    REDIS_URL               = "redis://${module.cache.redis_endpoint}:6379"
    BACKUP_BUCKET           = module.storage.backup_bucket_name
    AWS_REGION              = var.aws_region
    ENVIRONMENT             = var.environment
  }

  # Secrets (armazenadas en AWS Secrets Manager)
  secrets = {
    SECRET_KEY              = module.security.secret_key_arn
    DB_USERNAME             = module.security.db_credentials_arn
    DB_PASSWORD             = module.security.db_credentials_arn
    ANTHROPIC_API_KEY       = module.security.anthropic_api_key_arn
  }

  iam_role_arn             = module.security.ecs_task_execution_role_arn
  cloudwatch_log_group     = module.monitoring.ecs_log_group_name
  cloudwatch_log_retention = var.cloudwatch_log_retention

  depends_on = [
    module.database,
    module.cache,
    module.storage,
    module.security,
    module.lb
  ]
}

# ====================================================================
# Monitoring Module - CloudWatch, Alarms, Dashboards
# ====================================================================
module "monitoring" {
  source = "./modules/monitoring"

  environment                = var.environment
  ecs_cluster_name           = module.compute.ecs_cluster_name
  ecs_service_name           = module.compute.ecs_service_name
  rds_db_instance_id         = module.database.db_instance_id
  alb_target_group_arn       = module.lb.target_group_arn
  sns_topic_arn              = aws_sns_topic.alerts.arn
  cpu_threshold              = var.cpu_threshold
  memory_threshold           = var.memory_threshold
  db_latency_threshold       = var.db_latency_threshold
  cloudwatch_log_retention   = var.cloudwatch_log_retention
  enable_performance_insights = var.enable_performance_insights
}

# SNS Topic para notificaciones
resource "aws_sns_topic" "alerts" {
  name              = "${var.environment}-ticketdesk-alerts"
  kms_master_key_id = module.security.kms_key_id

  tags = {
    Name = "${var.environment}-alerts"
  }
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email

  # Nota: Requiere confirmación manual en email
}

# ====================================================================
# Auto Scaling - Target Tracking para ECS
# ====================================================================
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = var.ecs_max_capacity
  min_capacity       = var.ecs_min_capacity
  resource_id        = "service/${module.compute.ecs_cluster_name}/${module.compute.ecs_service_name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_policy_cpu" {
  name               = "${var.environment}-ecs-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

resource "aws_appautoscaling_policy" "ecs_policy_memory" {
  name               = "${var.environment}-ecs-memory-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value = 75.0
  }
}

# ====================================================================
# CloudFront Distribution para assets estáticos (opcional)
# ====================================================================
resource "aws_cloudfront_distribution" "cdn" {
  count = var.enable_cdn ? 1 : 0

  origin {
    domain_name = module.storage.backup_bucket_domain_name
    origin_id   = "S3Origin"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.oai[0].cloudfront_access_identity_path
    }
  }

  enabled             = true
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3Origin"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "${var.environment}-cdn"
  }
}

resource "aws_cloudfront_origin_access_identity" "oai" {
  count   = var.enable_cdn ? 1 : 0
  comment = "OAI para TicketDesk CDN"
}
