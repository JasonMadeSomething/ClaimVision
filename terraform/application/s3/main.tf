resource "aws_s3_bucket" "claimvision_bucket" {
  bucket = "claimvision-files-${var.aws_account_id}-${var.env}"

  tags = {
    Name = "ClaimVisionFiles-${var.env}"
  }
}

resource "aws_s3_bucket_policy" "claimvision_bucket_policy" {
  bucket = aws_s3_bucket.claimvision_bucket.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow"
        Principal = "*"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.claimvision_bucket.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket.claimvision_bucket]
}

locals {
  s3_bucket_name = aws_s3_bucket.claimvision_bucket.id
}

