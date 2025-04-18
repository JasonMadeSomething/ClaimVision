# VPC Endpoints for S3, SQS, Rekognition, and SSM

# S3 VPC Gateway Endpoint
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.claimvision_vpc.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.public_route_table.id]
  
  policy = jsonencode({
  Version = "2012-10-17",
  Statement = [
    {
      Effect    = "Allow",
      Principal = "*",
      Action    = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      Resource  = [
        "arn:aws:s3:::claimvision-files-*",
        "arn:aws:s3:::claimvision-files-*/*",
        "arn:aws:s3:::claimvision-reports-*",
        "arn:aws:s3:::claimvision-reports-*/*"
      ]
    }
  ]
})

  tags = {
    Name = "ClaimVisionS3Endpoint-${var.env}"
  }
}

# SQS VPC Interface Endpoint
resource "aws_vpc_endpoint" "sqs" {
  vpc_id             = aws_vpc.claimvision_vpc.id
  service_name       = "com.amazonaws.${var.region}.sqs"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]
  security_group_ids = [aws_security_group.vpc_endpoint_sg.id]
  private_dns_enabled = true
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl"
        ]
        Resource  = [
          "arn:aws:sqs:us-east-1:337214855826:claimvision-file-upload-queue-dev",
          "arn:aws:sqs:us-east-1:337214855826:claimvision-file-analysis-queue-dev",
          "arn:aws:sqs:us-east-1:337214855826:claimvision-user-registration-queue",
          "arn:aws:sqs:us-east-1:337214855826:claimvision-cognito-update-queue",
          "arn:aws:sqs:us-east-1:337214855826:claimvision-report-request-queue-dev",
          "arn:aws:sqs:us-east-1:337214855826:claimvision-file-organization-queue-dev",
          "arn:aws:sqs:us-east-1:337214855826:claimvision-deliver-report-queue-dev",
          "arn:aws:sqs:us-east-1:337214855826:claimvision-email-queue-dev"
        ]
      }
    ]
  })

  tags = {
    Name = "ClaimVisionSQSEndpoint-${var.env}"
  }
}

# Rekognition VPC Interface Endpoint
resource "aws_vpc_endpoint" "rekognition" {
  vpc_id             = aws_vpc.claimvision_vpc.id
  service_name       = "com.amazonaws.${var.region}.rekognition"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]
  security_group_ids = [aws_security_group.vpc_endpoint_sg.id]
  private_dns_enabled = true
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = [
          "rekognition:DetectLabels",
          "rekognition:DetectText"
        ]
        Resource  = "*"
      }
    ]
  })

  tags = {
    Name = "ClaimVisionRekognitionEndpoint-${var.env}"
  }
}

# SSM Parameter Store VPC Interface Endpoint
resource "aws_vpc_endpoint" "ssm" {
  vpc_id             = aws_vpc.claimvision_vpc.id
  service_name       = "com.amazonaws.${var.region}.ssm"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]
  security_group_ids = [aws_security_group.vpc_endpoint_sg.id]
  private_dns_enabled = true
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource  = [
          "arn:aws:ssm:${var.region}:*:parameter/terraform/*",
          "arn:aws:ssm:${var.region}:*:parameter/claimvision/*"
        ]
      }
    ]
  })

  tags = {
    Name = "ClaimVisionSSMEndpoint-${var.env}"
  }
}

# Security Group for VPC Endpoints
resource "aws_security_group" "vpc_endpoint_sg" {
  name        = "vpc-endpoint-sg-${var.env}"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.claimvision_vpc.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "Allow HTTPS from VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name = "ClaimVisionVPCEndpointSG-${var.env}"
  }
}