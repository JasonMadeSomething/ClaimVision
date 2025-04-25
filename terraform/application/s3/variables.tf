variable "env" {
  type        = string
  description = "Environment name (e.g., dev, prod)"
}
variable "aws_account_id" {
  type        = string
  description = "AWS account ID"
}

variable "process_uploaded_file_lambda_arn" {
  type        = string
  description = "ARN of the process_uploaded_file Lambda function"
  default     = ""
}
