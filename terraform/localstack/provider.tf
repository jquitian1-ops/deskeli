terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend local para desarrollo
  backend "local" {
    path = "terraform.tfstate"
  }
}

provider "aws" {
  region = var.aws_region

  # Configuración LocalStack
  endpoints {
    ec2       = var.localstack_endpoint
    ecs       = var.localstack_endpoint
    rds       = var.localstack_endpoint
    s3        = var.localstack_endpoint
    elb       = var.localstack_endpoint
    elbv2     = var.localstack_endpoint
    cloudformation = var.localstack_endpoint
    iam       = var.localstack_endpoint
    cloudwatch    = var.localstack_endpoint
    logs      = var.localstack_endpoint
    secretsmanager = var.localstack_endpoint
    sqs       = var.localstack_endpoint
    sns       = var.localstack_endpoint
  }

  # Credenciales dummy (LocalStack no valida)
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key

  # Skip validación de credenciales
  skip_credentials_validation = true
  skip_metadata_api_check      = true
  skip_region_validation       = true
  skip_requesting_account_id   = true

  default_tags {
    tags = {
      Environment = var.environment
      Project     = "TicketDesk"
      ManagedBy   = "Terraform"
      CreatedAt   = timestamp()
    }
  }
}

# Configuración de proveedores locales (para desarrollo)
provider "local" {
  version = "~> 2.0"
}

variable "localstack_endpoint" {
  description = "Endpoint de LocalStack"
  type        = string
  default     = "http://localhost:4566"
}

variable "aws_region" {
  description = "AWS Region para LocalStack"
  type        = string
  default     = "us-east-1"
}

variable "aws_access_key" {
  description = "AWS Access Key (dummy para LocalStack)"
  type        = string
  default     = "test"
  sensitive   = true
}

variable "aws_secret_key" {
  description = "AWS Secret Key (dummy para LocalStack)"
  type        = string
  default     = "test"
  sensitive   = true
}

variable "environment" {
  description = "Entorno (dev, staging, prod)"
  type        = string
  default     = "dev"
}
