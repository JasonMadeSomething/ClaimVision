output "ses_identity_arn" {
  value = aws_ses_email_identity.report_sender.arn
}

output "ses_sender_email" {
  value = var.sender_email
}
