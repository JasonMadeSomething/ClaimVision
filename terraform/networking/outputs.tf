output "vpc_id" {
  value = aws_vpc.claimvision_vpc.id
}

output "public_subnet_1" {
  value = aws_subnet.public_subnet_1.id
}

output "public_subnet_2" {
  value = aws_subnet.public_subnet_2.id
}

output "rds_security_group_id" {
  value = aws_security_group.rds_sg.id
}

