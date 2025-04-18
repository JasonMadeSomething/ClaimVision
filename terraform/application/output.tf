output "rds_endpoint" {
  value = module.rds.rds_endpoint
}

output "s3_bucket_name" {
  value = module.s3.s3_bucket_name
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

output "reports_bucket_name" {
  value = module.s3.reports_bucket_name
}

output "report_request_queue_url" {
  value = module.sqs.report_request_queue_url
}

output "report_request_queue_arn" {
  value = module.sqs.report_request_queue_arn
}

output "file_organization_queue_url" {
  value = module.sqs.file_organization_queue_url
}

output "file_organization_queue_arn" {
  value = module.sqs.file_organization_queue_arn
}

output "efs_access_point_arn" {
  value = module.efs.efs_access_point_arn
}

output "efs_file_system_id" {
  value = module.efs.efs_file_system_id
}

output "deliver_report_queue_url" {
  value = module.sqs.deliver_report_queue_url
}

output "deliver_report_queue_arn" {
  value = module.sqs.deliver_report_queue_arn
}

output "email_queue_url" {
  description = "URL of the email queue"
  value       = module.sqs.email_queue_url
}

output "email_queue_arn" {
  description = "ARN of the email queue"
  value       = module.sqs.email_queue_arn
}

output "email_queue_name" {
  description = "Name of the email queue"
  value       = module.sqs.email_queue_name
}
