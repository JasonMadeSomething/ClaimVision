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
