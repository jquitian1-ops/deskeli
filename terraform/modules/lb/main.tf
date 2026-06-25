# ====================================================================
# Load Balancer Module - Application Load Balancer
# ====================================================================
# Configura ALB con target groups, listeners HTTPS y health checks

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ====================================================================
# Application Load Balancer
# ====================================================================
resource "aws_lb" "main" {
  name               = "${var.environment}-ticketdesk-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = var.environment == "prod" ? true : false
  enable_http2              = true
  enable_cross_zone_load_balancing = true

  tags = {
    Name = "${var.environment}-alb"
  }
}

# ====================================================================
# Target Group
# ====================================================================
resource "aws_lb_target_group" "main" {
  name        = "${var.environment}-ticketdesk-tg"
  port        = var.app_port
  protocol    = var.app_protocol
  vpc_id      = var.vpc_id
  target_type = "ip"  # Para Fargate

  health_check {
    healthy_threshold   = var.healthy_threshold
    unhealthy_threshold = var.unhealthy_threshold
    timeout             = var.health_check_timeout
    interval            = var.health_check_interval
    path                = var.health_check_path
    matcher             = "200-399"  # Aceptar 2xx y 3xx
    port                = "traffic-port"
  }

  stickiness {
    type            = "lb_cookie"
    enabled         = true
    cookie_duration = 86400  # 24h
  }

  deregistration_delay = 30

  tags = {
    Name = "${var.environment}-tg"
  }
}

# ====================================================================
# Listener HTTP (redirigir a HTTPS)
# ====================================================================
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# ====================================================================
# Listener HTTPS
# ====================================================================
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.enable_https ? var.certificate_arn : null

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
}

# ====================================================================
# Listener Rule para health check sin redirect
# ====================================================================
resource "aws_lb_listener_rule" "health" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 1

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }

  condition {
    path_pattern {
      values = ["/api/health", "/health"]
    }
  }
}

# ====================================================================
# CloudWatch Alarms para ALB
# ====================================================================
resource "aws_cloudwatch_metric_alarm" "alb_target_response_time" {
  alarm_name          = "${var.environment}-alb-slow-response"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "1"  # 1 segundo
  alarm_description   = "Alerta cuando tiempo de respuesta ALB > 1s"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_hosts" {
  alarm_name          = "${var.environment}-alb-unhealthy-hosts"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "2"
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "1"
  alarm_description   = "Alerta cuando hay hosts unhealthy"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
    TargetGroup  = aws_lb_target_group.main.arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_request_count" {
  alarm_name          = "${var.environment}-alb-high-requests"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "RequestCount"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10000"
  alarm_description   = "Alerta cuando hay >10k requests por 5 min"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
}
