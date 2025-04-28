output "s3_bucket_name" {
  value = local.s3_bucket_name
}

output "reports_bucket_name" {
  value = local.reports_bucket_name
}

output "s3_bucket_id" {
  value = aws_s3_bucket.claimvision_bucket.id
}

output "s3_bucket_arn" {
  value = aws_s3_bucket.claimvision_bucket.arn
}