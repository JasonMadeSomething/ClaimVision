output "db_username_ssm_path" {
  description = "The SSM parameter path for the database username"
  value       = aws_ssm_parameter.db_username.name
}

output "db_password_ssm_path" {
  description = "The SSM parameter path for the database password"
  value       = aws_ssm_parameter.db_password.name
}

output "rds_endpoint_ssm_path" {
  description = "The SSM parameter path for the RDS endpoint"
  value       = aws_ssm_parameter.db_host.name
}

output "s3_bucket_name_ssm_path" {
  description = "The SSM parameter path for the S3 bucket name"
  value       = aws_ssm_parameter.s3_bucket_name.name
}
