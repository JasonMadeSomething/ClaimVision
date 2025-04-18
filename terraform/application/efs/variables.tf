variable "env" {
  description = "Environment (dev, prod)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_1" {
  description = "First public subnet ID"
  type        = string
}

variable "public_subnet_2" {
  description = "Second public subnet ID"
  type        = string
}

variable "lambda_security_group_id" {
  description = "Security group ID for Lambda functions"
  type        = string
}