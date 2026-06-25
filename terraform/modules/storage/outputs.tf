# ====================================================================
# Storage Module - Outputs
# ====================================================================

output "backup_bucket_name" {
  description = "Nombre del bucket S3 para backups"
  value       = aws_s3_bucket.backups.id
}

output "backup_bucket_arn" {
  description = "ARN del bucket S3"
  value       = aws_s3_bucket.backups.arn
}

output "backup_bucket_domain_name" {
  description = "Domain name del bucket S3"
  value       = aws_s3_bucket.backups.bucket_regional_domain_name
}

output "backup_bucket_region" {
  description = "Región del bucket S3"
  value       = aws_s3_bucket.backups.region
}

output "logs_bucket_name" {
  description = "Nombre del bucket S3 para logs"
  value       = aws_s3_bucket.logs.id
}

output "logs_bucket_arn" {
  description = "ARN del bucket de logs"
  value       = aws_s3_bucket.logs.arn
}
