variable "env" {
  type        = string
  description = "Environment name (e.g., dev, prod)"
}

variable "db_username" {
  type        = string
  description = "Database username"
}

variable "db_password" {
  type        = string
  description = "Database password"
  sensitive   = true  # ✅ Hides value in Terraform output
}
variable "public_subnet_1" {
  type = string
}

variable "public_subnet_2" {
  type = string
}

variable "rds_security_group_id" {
  type = string
}
