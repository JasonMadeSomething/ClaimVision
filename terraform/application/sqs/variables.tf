variable "env" {
  type        = string
  description = "Environment name (e.g., dev, prod)"
}

variable "environment" {
  type        = string
  description = "Environment name for tagging (e.g., dev, prod)"
  default     = "dev"
}

variable "s3_bucket_id" {
  type        = string
  description = "ID of the S3 bucket for file uploads"
}

variable "s3_bucket_arn" {
  type        = string
  description = "ARN of the S3 bucket for file uploads"
}
