# ✅ Networking Outputs
output "vpc_id" {
  value = module.networking.vpc_id
}

output "public_subnet_1" {
  value = module.networking.public_subnet_1
}

output "public_subnet_2" {
  value = module.networking.public_subnet_2
}

output "rds_security_group_id" {
  value = module.networking.rds_security_group_id
}

# ✅ Application Outputs
output "rds_endpoint" {
  value = module.application.rds_endpoint
}

output "s3_bucket_name" {
  value = module.application.s3_bucket_name
}

# ✅ SSM Parameter Paths
output "db_username_ssm_path" {
  value = module.application.db_username_ssm_path
}

output "db_password_ssm_path" {
  value = module.application.db_password_ssm_path
}

output "rds_endpoint_ssm_path" {
  value = module.application.rds_endpoint_ssm_path
}

# ✅ SQS Queues
output "file_upload_queue_url" {
  value = module.application.file_upload_queue_url
}

output "file_upload_queue_arn" {
  value = module.application.file_upload_queue_arn
}

output "file_analysis_queue_url" {
  value = module.application.file_analysis_queue_url
}

output "file_analysis_queue_arn" {
  value = module.application.file_analysis_queue_arn
}

output "user_registration_queue_url" {
  value = module.application.user_registration_queue_url
}

output "cognito_update_queue_url" {
  description = "The URL of the Cognito update queue"
  value       = module.application.cognito_update_queue_url
}

# Reporting Infrastructure Outputs
output "reports_bucket_name" {
  description = "The name of the S3 bucket for storing reports"
  value       = module.application.reports_bucket_name
}

output "report_request_queue_url" {
  description = "The URL of the report request queue"
  value       = module.application.report_request_queue_url
}

output "report_request_queue_arn" {
  description = "The ARN of the report request queue"
  value       = module.application.report_request_queue_arn
}

output "file_organization_queue_url" {
  description = "The URL of the file organization queue"
  value       = module.application.file_organization_queue_url
}

output "file_organization_queue_arn" {
  description = "The ARN of the file organization queue"
  value       = module.application.file_organization_queue_arn
}

output "efs_access_point_arn" {
  description = "The ARN of the EFS access point for report files"
  value       = module.application.efs_access_point_arn
}

output "efs_file_system_id" {
  description = "The ID of the EFS file system for report files"
  value       = module.application.efs_file_system_id
}

output "deliver_report_queue_url" {
  description = "The URL of the deliver report queue"
  value       = module.application.deliver_report_queue_url
}

output "deliver_report_queue_arn" {
  description = "ARN of the deliver report queue"
  value       = module.application.deliver_report_queue_arn
}

output "email_queue_url" {
  description = "URL of the email queue"
  value       = module.application.email_queue_url
}

output "email_queue_arn" {
  description = "ARN of the email queue"
  value       = module.application.email_queue_arn
}

output "email_queue_name" {
  description = "Name of the email queue"
  value       = module.application.email_queue_name
}