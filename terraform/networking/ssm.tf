# SSM Parameter for VPC ID
resource "aws_ssm_parameter" "vpc_id" {
  name  = "/terraform/networking/vpc_id"
  type  = "String"
  value = aws_vpc.claimvision_vpc.id
  lifecycle {
    ignore_changes = [value]
  }
}

# SSM Parameter for Public Subnet 1
resource "aws_ssm_parameter" "public_subnet_1" {
  name  = "/terraform/networking/public_subnet_1"
  type  = "String"
  value = aws_subnet.public_subnet_1.id
  lifecycle {
    ignore_changes = [value]
  }
}

# SSM Parameter for Public Subnet 2
resource "aws_ssm_parameter" "public_subnet_2" {
  name  = "/terraform/networking/public_subnet_2"
  type  = "String"
  value = aws_subnet.public_subnet_2.id
  lifecycle {
    ignore_changes = [value]
  }
}

# SSM Parameter for RDS Security Group ID
resource "aws_ssm_parameter" "rds_security_group_id" {
  name  = "/terraform/networking/rds_sg_id"
  type  = "String"
  value = aws_security_group.rds_sg.id
  lifecycle {
    ignore_changes = [value]
  }
}
