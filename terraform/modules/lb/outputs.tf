# ====================================================================
# Load Balancer Module - Outputs
# ====================================================================

output "alb_id" {
  description = "ID del Application Load Balancer"
  value       = aws_lb.main.id
}

output "alb_arn" {
  description = "ARN del ALB"
  value       = aws_lb.main.arn
}

output "alb_dns_name" {
  description = "DNS name del ALB"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Hosted Zone ID del ALB"
  value       = aws_lb.main.zone_id
}

output "target_group_arn" {
  description = "ARN del Target Group"
  value       = aws_lb_target_group.main.arn
}

output "target_group_id" {
  description = "ID del Target Group"
  value       = aws_lb_target_group.main.id
}

output "target_group_name" {
  description = "Nombre del Target Group"
  value       = aws_lb_target_group.main.name
}

output "http_listener_arn" {
  description = "ARN del HTTP listener"
  value       = aws_lb_listener.http.arn
}

output "https_listener_arn" {
  description = "ARN del HTTPS listener"
  value       = aws_lb_listener.https.arn
}
