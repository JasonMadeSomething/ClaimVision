output "db_username_ssm_path" {
  description = "The SSM parameter path for the database username"
  value       = module.ssm.db_username_ssm_path
}

output "db_password_ssm_path" {
  description = "The SSM parameter path for the database password"
  value       = module.ssm.db_password_ssm_path
}

output "rds_endpoint_ssm_path" {
  description = "The SSM parameter path for the RDS endpoint"
  value       = module.ssm.rds_endpoint_ssm_path
}
