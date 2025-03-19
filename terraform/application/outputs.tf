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

output "file_upload_queue_url" {
  value = module.sqs.file_upload_queue_url
}

output "file_upload_queue_arn" {
  value = module.sqs.file_upload_queue_arn
}

output "file_analysis_queue_url" {
  value = module.sqs.file_analysis_queue_url
}

output "file_analysis_queue_arn" {
  value = module.sqs.file_analysis_queue_arn
}

output "user_registration_queue_url" {
  value = module.sqs.user_registration_queue_url
}

output "user_registration_queue_arn" {
  value = module.sqs.user_registration_queue_arn
}

output "user_registration_queue_name" {
  value = module.sqs.user_registration_queue_name
}
