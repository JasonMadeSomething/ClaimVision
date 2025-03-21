variable "env" {
  type        = string
  description = "Environment name (e.g., dev, prod)"
}

variable "environment" {
  type        = string
  description = "Environment name for tagging (e.g., dev, prod)"
  default     = "dev"
}
