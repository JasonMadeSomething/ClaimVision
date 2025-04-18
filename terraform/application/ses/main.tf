resource "aws_ses_email_identity" "report_sender" {
  email = var.sender_email
}

# Optional: Set up domain identity if you haven't already
resource "aws_ses_domain_identity" "domain_identity" {
  domain = var.domain_name
}

# Optional: Configure DKIM
resource "aws_ses_domain_dkim" "domain_dkim" {
  domain = aws_ses_domain_identity.domain_identity.domain
}