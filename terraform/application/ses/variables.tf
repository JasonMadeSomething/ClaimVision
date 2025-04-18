variable "env" {
  description = "Environment (dev, prod)"
  type        = string
}

variable "domain_name" {
  description = "Domain name for SES configuration"
  type        = string
  default     = "made-something.com"
}

variable "sender_email" {
  description = "Email address to use as the sender for reports"
  type        = string
  default     = "reports@made-something.com"
}
