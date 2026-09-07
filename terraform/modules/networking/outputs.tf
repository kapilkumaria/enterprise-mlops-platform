output "vpc_id" {
  description = "ID of the created VPC."
  value       = aws_vpc.this.id
}

output "vpc_cidr" {
  description = "CIDR block assigned to the VPC."
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets."
  value       = aws_subnet.private[*].id
}

output "nat_gateway_id" {
  description = "ID of the development NAT Gateway."
  value       = aws_nat_gateway.this.id
}

output "internet_gateway_id" {
  description = "ID of the VPC Internet Gateway."
  value       = aws_internet_gateway.this.id
}
