variable "env" {}

variable "vpc_id" {}
variable "public_subnet_1" {
  type = string
}

variable "public_subnet_2" {
  type = string
}

variable "rds_security_group_id" {}

# These are now passed from the top-level module!
variable "db_username" {
  type        = string
  description = "Database username"
  default     = "testuser"  # Set a default or pass it in `terraform.tfvars`
}

variable "db_password" {
  type        = string
  description = "Database password"
  sensitive   = true
}

variable "aws_account_id" {
  type        = string
  description = "AWS Account ID"
}

variable "aws_region" {
  type        = string
  description = "AWS Region"
}

variable "lambda_security_group_id" {
  type        = string
  description = "Security group ID for Lambda functions"
  default     = ""
}

variable "domain_name" {
  type        = string
  description = "Domain name for SES configuration"
  default     = "claimvision.made-something.com"
}

variable "sender_email" {
  type        = string
  description = "Email address to use as the sender for reports"
  default     = "reports@claimvision.made-something.com"
}
