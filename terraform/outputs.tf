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

output "user_registration_queue_arn" {
  value = module.application.user_registration_queue_arn
}

output "user_registration_queue_name" {
  value = module.application.user_registration_queue_name
}
