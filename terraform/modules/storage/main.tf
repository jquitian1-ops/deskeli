# ====================================================================
# Storage Module - S3 para Backups
# ====================================================================
# Configura bucket S3 con versionado, encriptación y políticas de ciclo de vida

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ====================================================================
# S3 Bucket para Backups
# ====================================================================
resource "aws_s3_bucket" "backups" {
  bucket = "${var.environment}-ticketdesk-backups-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${var.environment}-backups"
  }
}

# Block Public Access
resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ====================================================================
# Versionado
# ====================================================================
resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id

  versioning_configuration {
    status     = var.enable_versioning ? "Enabled" : "Suspended"
    mfa_delete = var.mfa_delete_required ? "Enabled" : "Disabled"
  }
}

# ====================================================================
# Encriptación en Reposo
# ====================================================================
resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = true
  }
}

# ====================================================================
# Logging
# ====================================================================
resource "aws_s3_bucket_logging" "backups" {
  bucket = aws_s3_bucket.backups.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "backups/"
}

resource "aws_s3_bucket" "logs" {
  bucket = "${var.environment}-ticketdesk-logs-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${var.environment}-logs"
  }
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ====================================================================
# Lifecycle Policy (retención de backups)
# ====================================================================
resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  count  = var.enable_lifecycle_policy ? 1 : 0
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "delete-old-backups"
    status = "Enabled"

    # Eliminar versiones antiguas después de X días
    noncurrent_version_expiration {
      noncurrent_days = var.backup_retention_days
    }

    # Transición a GLACIER después de 30 días
    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    # Eliminar completamente después de retención
    expiration {
      days = var.backup_retention_days
    }
  }
}

# ====================================================================
# CORS (para acceso desde frontend, si aplica)
# ====================================================================
resource "aws_s3_bucket_cors_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET"]
    allowed_origins = ["*"]  # Restringir en producción
    max_age_seconds = 3000
  }
}

# ====================================================================
# Bucket Policy (acceso para aplicación)
# ====================================================================
resource "aws_s3_bucket_policy" "backups" {
  bucket = aws_s3_bucket.backups.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyInsecureTransport"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.backups.arn,
          "${aws_s3_bucket.backups.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid    = "AllowAppAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*"
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:GetObjectVersion"
        ]
        Resource = [
          aws_s3_bucket.backups.arn,
          "${aws_s3_bucket.backups.arn}/*"
        ]
      }
    ]
  })
}

# ====================================================================
# CloudWatch Alarms
# ====================================================================
resource "aws_cloudwatch_metric_alarm" "backup_bucket_size" {
  alarm_name          = "${var.environment}-backup-bucket-size"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "BucketSizeBytes"
  namespace           = "AWS/S3"
  period              = "86400"  # Daily
  statistic           = "Average"
  threshold           = 107374182400  # 100 GB
  alarm_description   = "Alerta cuando bucket de backups > 100 GB"

  dimensions = {
    BucketName = aws_s3_bucket.backups.id
    StorageType = "StandardStorage"
  }
}

# ====================================================================
# Data Sources
# ====================================================================
data "aws_caller_identity" "current" {}
