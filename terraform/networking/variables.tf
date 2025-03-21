variable "public_ip" {
  type        = string
  description = "Your local public IP for RDS access"
}
variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the VPC"
  default     = "10.0.0.0/16"
}
variable "env" {
  type        = string
  description = "Environment name (e.g., dev, prod)"
}
variable "region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}
