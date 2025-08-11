output "file_upload_queue_url" {
  value = aws_sqs_queue.file_upload_queue.url
}

output "file_upload_queue_arn" {
  value = aws_sqs_queue.file_upload_queue.arn
}

output "file_analysis_queue_url" {
  value = aws_sqs_queue.file_analysis_queue.url
}

output "file_analysis_queue_arn" {
  value = aws_sqs_queue.file_analysis_queue.arn
}

output "file_analysis_queue_name" {
  description = "Name of the file analysis queue"
  value       = aws_sqs_queue.file_analysis_queue.name
}

output "user_registration_queue_url" {
  value = aws_sqs_queue.user_registration_queue.url
}

output "user_registration_queue_arn" {
  value = aws_sqs_queue.user_registration_queue.arn
}

output "user_registration_queue_name" {
  description = "The name of the user registration queue"
  value       = aws_sqs_queue.user_registration_queue.name
}

output "cognito_update_queue_url" {
  description = "The URL of the Cognito update queue"
  value       = aws_sqs_queue.cognito_update_queue.url
}

output "cognito_update_queue_arn" {
  description = "The ARN of the Cognito update queue"
  value       = aws_sqs_queue.cognito_update_queue.arn
}

output "cognito_update_queue_name" {
  description = "The name of the Cognito update queue"
  value       = aws_sqs_queue.cognito_update_queue.name
}

output "report_request_queue_url" {
  description = "The URL of the report request queue"
  value       = aws_sqs_queue.report_request_queue.url
}

output "report_request_queue_arn" {
  description = "The ARN of the report request queue"
  value       = aws_sqs_queue.report_request_queue.arn
}

output "report_request_queue_name" {
  description = "The name of the report request queue"
  value       = aws_sqs_queue.report_request_queue.name
}

output "file_organization_queue_url" {
  description = "The URL of the file organization queue"
  value       = aws_sqs_queue.file_organization_queue.url
}

output "file_organization_queue_arn" {
  description = "The ARN of the file organization queue"
  value       = aws_sqs_queue.file_organization_queue.arn
}

output "file_organization_queue_name" {
  description = "The name of the file organization queue"
  value       = aws_sqs_queue.file_organization_queue.name
}

output "email_queue_url" {
  description = "URL of the email queue"
  value       = aws_sqs_queue.email_queue.url
}

output "email_queue_arn" {
  description = "ARN of the email queue"
  value       = aws_sqs_queue.email_queue.arn
}

output "email_queue_name" {
  description = "Name of the email queue"
  value       = aws_sqs_queue.email_queue.name
}

output "deliver_report_queue_url" {
  value = aws_sqs_queue.deliver_report_queue.id
}

output "deliver_report_queue_arn" {
  value = aws_sqs_queue.deliver_report_queue.arn
}

output "s3_upload_notification_queue_url" {
  value = aws_sqs_queue.s3_upload_notification_queue.url
}

output "s3_upload_notification_queue_arn" {
  value = aws_sqs_queue.s3_upload_notification_queue.arn
}

output "s3_upload_notification_queue_name" {
  description = "Name of the S3 upload notification queue"
  value       = aws_sqs_queue.s3_upload_notification_queue.name
}

output "outbound_messages_queue_url" {
  description = "URL of the outbound messages queue"
  value       = aws_sqs_queue.outbound_messages.url
}

output "outbound_messages_queue_arn" {
  description = "ARN of the outbound messages queue"
  value       = aws_sqs_queue.outbound_messages.arn
}

output "outbound_messages_queue_name" {
  description = "Name of the outbound messages queue"
  value       = aws_sqs_queue.outbound_messages.name
}

output "batch_tracking_queue_url" {
  description = "URL of the batch tracking queue"
  value       = aws_sqs_queue.batch_tracking.url
}

output "batch_tracking_queue_arn" {
  description = "ARN of the batch tracking queue"
  value       = aws_sqs_queue.batch_tracking.arn
}

output "batch_tracking_queue_name" {
  description = "Name of the batch tracking queue"
  value       = aws_sqs_queue.batch_tracking.name
}