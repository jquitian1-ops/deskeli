variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Entorno (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block para VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block para subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "ticketdesk"
  sensitive   = true
}

variable "db_password" {
  description = "Database password"
  type        = string
  default     = "ticketdesk123"
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "anthropic_api_key" {
  description = "Anthropic API Key para Claude"
  type        = string
  default     = ""
  sensitive   = true
}

variable "teams_webhook_url" {
  description = "Microsoft Teams Webhook URL"
  type        = string
  default     = ""
  sensitive   = true
}

variable "tags" {
  description = "Tags comunes para todos los recursos"
  type        = map(string)
  default = {
    Project     = "TicketDesk"
    Environment = "development"
    ManagedBy   = "Terraform"
  }
}
