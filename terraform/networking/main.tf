# main.tf (Networking Resources)

# VPC
resource "aws_vpc" "claimvision_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "ClaimVisionVPC-${var.env}"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "claimvision_igw" {
  vpc_id = aws_vpc.claimvision_vpc.id
  tags = {
    Name = "ClaimVisionIGW-${var.env}"
  }
}

# Public Subnets
resource "aws_subnet" "public_subnet_1" {
  vpc_id                  = aws_vpc.claimvision_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "us-east-1a"
  tags = {
    Name = "ClaimVisionPublicSubnet1-${var.env}"
  }
}

resource "aws_subnet" "public_subnet_2" {
  vpc_id                  = aws_vpc.claimvision_vpc.id
  cidr_block              = "10.0.2.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "us-east-1b"
  tags = {
    Name = "ClaimVisionPublicSubnet2-${var.env}"
  }
}

# Public Route Table
resource "aws_route_table" "public_route_table" {
  vpc_id = aws_vpc.claimvision_vpc.id
  tags = {
    Name = "ClaimVisionPublicRouteTable-${var.env}"
  }
}

# Route to Internet Gateway
resource "aws_route" "public_route" {
  route_table_id         = aws_route_table.public_route_table.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.claimvision_igw.id
}

# Associate Public Subnets with Route Table
resource "aws_route_table_association" "public_subnet_1_assoc" {
  subnet_id      = aws_subnet.public_subnet_1.id
  route_table_id = aws_route_table.public_route_table.id
}

resource "aws_route_table_association" "public_subnet_2_assoc" {
  subnet_id      = aws_subnet.public_subnet_2.id
  route_table_id = aws_route_table.public_route_table.id
}

# Security Group for RDS
resource "aws_security_group" "rds_sg" {
  vpc_id = aws_vpc.claimvision_vpc.id
  name   = "ClaimVisionRDS-SG-${var.env}"

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.public_ip]
  }
}
