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