# ====================================================================
# VPC Module - Outputs
# ====================================================================

output "vpc_id" {
  description = "ID de la VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "CIDR block de la VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs de las subnets públicas"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs de las subnets privadas"
  value       = aws_subnet.private[*].id
}

output "internet_gateway_id" {
  description = "ID del Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "nat_gateway_ids" {
  description = "IDs de los NAT Gateways"
  value       = aws_nat_gateway.main[*].id
}

output "nat_gateway_ip" {
  description = "IP Elástica del NAT Gateway (primera)"
  value       = var.enable_nat_gateway ? aws_eip.nat[0].public_ip : null
}

output "public_route_table_id" {
  description = "ID de la route table pública"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "IDs de las route tables privadas"
  value       = aws_route_table.private[*].id
}

output "s3_endpoint_id" {
  description = "ID del VPC Endpoint S3"
  value       = aws_vpc_endpoint.s3.id
}

output "logs_endpoint_id" {
  description = "ID del VPC Endpoint CloudWatch Logs"
  value       = aws_vpc_endpoint.logs.id
}

output "vpc_endpoints_security_group_id" {
  description = "ID del security group para VPC Endpoints"
  value       = aws_security_group.vpc_endpoints.id
}
