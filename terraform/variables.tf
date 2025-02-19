variable "env" {
  type        = string
  description = "Environment name (e.g., dev, prod)"
}

variable "aws_region" {
  type        = string
  description = "AWS region where resources will be deployed"
  default     = "us-east-1"
}


# ✅ Database Credentials (Used in Application Module)
variable "db_username" {
  type        = string
  description = "Username for RDS database"
  default     = "testuser"
}

variable "db_password" {
  type        = string
  description = "Database password"
  sensitive   = true
}

# ✅ Feature Flags
variable "enable_cognito" {
  type        = bool
  description = "Enable Cognito for authentication"
  default     = true
}

variable "public_ip" {
  type        = string
  description = "Public IP of the machine running Terraform (for RDS security group)"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the VPC"
  default     = "10.0.0.0/16"
}
