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
  value = aws_sqs_queue.user_registration_queue.name
}
