variable "env" {
  type        = string
  description = "Environment name (e.g., dev, prod)"
}

variable "s3_bucket_name" {
  type        = string
  description = "S3 bucket for file storage"
}

variable "rds_endpoint" {
  type        = string
  description = "RDS database endpoint"
}

variable "db_username" {
  type        = string
  description = "Database username"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "Database password from Secrets Manager"
}

variable "aws_region" {
  type        = string
  description = "AWS region"
}
