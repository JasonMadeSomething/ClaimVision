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

output "user_registration_queue_url" {
  value = module.sqs.user_registration_queue_url
}

output "user_registration_queue_arn" {
  value = module.sqs.user_registration_queue_arn
}

output "cognito_update_queue_url" {
  description = "The URL of the Cognito update queue"
  value       = module.sqs.cognito_update_queue_url
}

output "cognito_update_queue_arn" {
  value = module.sqs.cognito_update_queue_arn
}

output "outbound_messages_queue_url" {
  value = module.sqs.outbound_messages_queue_url
}

output "outbound_messages_queue_arn" {
  value = module.sqs.outbound_messages_queue_arn
}

output "outbound_messages_queue_name" {
  value = module.sqs.outbound_messages_queue_name
}

output "batch_tracking_queue_url" {
  value = module.sqs.batch_tracking_queue_url
}

output "batch_tracking_queue_arn" {
  value = module.sqs.batch_tracking_queue_arn
}

output "batch_tracking_queue_name" {
  value = module.sqs.batch_tracking_queue_name
}

output "s3_upload_notification_queue_url" {
  value = module.sqs.s3_upload_notification_queue_url
}

output "s3_upload_notification_queue_arn" {
  value = module.sqs.s3_upload_notification_queue_arn
}
