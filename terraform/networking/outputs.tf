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

output "s3_vpc_endpoint_id" {
  value = aws_vpc_endpoint.s3.id
  description = "ID of the S3 VPC Gateway Endpoint"
}

output "sqs_vpc_endpoint_id" {
  value = aws_vpc_endpoint.sqs.id
  description = "ID of the SQS VPC Interface Endpoint"
}

output "vpc_endpoint_security_group_id" {
  value = aws_security_group.vpc_endpoint_sg.id
  description = "ID of the security group for VPC endpoints"
}

output "public_route_table_id" {
  value = aws_route_table.public_route_table.id
  description = "ID of the public route table"
}

output "rekognition_vpc_endpoint_id" {
  value = aws_vpc_endpoint.rekognition.id
  description = "ID of the Rekognition VPC Interface Endpoint"
}
