locals {
  claimvision_bucket_arn = aws_s3_bucket.claimvision_bucket.arn
  reports_bucket_arn     = aws_s3_bucket.reports_bucket.arn
  s3_bucket_name = aws_s3_bucket.claimvision_bucket.id
  reports_bucket_name = aws_s3_bucket.reports_bucket.id
}

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
        Sid       = "AllowObjectAccessForClaimVisionRoles",
        Effect    = "Allow",
        Principal = "*",
        Action    = [
          "s3:GetObject",
          "s3:PutObject"
        ],
        Resource  = [
          "${local.claimvision_bucket_arn}/*"
        ],
        Condition = {
          StringLike = {
            "aws:PrincipalArn" = "arn:aws:iam::${var.aws_account_id}:role/ClaimVision-*"
          }
        }
      },
      {
        Sid       = "AllowListBucketForClaimVisionRoles",
        Effect    = "Allow",
        Principal = "*",
        Action    = "s3:ListBucket",
        Resource  = local.claimvision_bucket_arn,
        Condition = {
          StringLike = {
            "aws:PrincipalArn" = "arn:aws:iam::${var.aws_account_id}:role/ClaimVision-*"
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket.claimvision_bucket]
}

resource "aws_s3_bucket" "reports_bucket" {
  bucket = "claimvision-reports-${var.aws_account_id}-${var.env}"

  tags = {
    Name = "ClaimVisionReports-${var.env}"
  }
}

resource "aws_s3_bucket_policy" "reports_bucket_policy" {
  bucket = aws_s3_bucket.reports_bucket.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "AllowObjectAccessForClaimVisionRoles",
        Effect    = "Allow",
        Principal = "*",
        Action    = [
          "s3:GetObject",
          "s3:PutObject"
        ],
        Resource  = [
          "${local.reports_bucket_arn}/*"
        ],
        Condition = {
          StringLike = {
            "aws:PrincipalArn" = "arn:aws:iam::${var.aws_account_id}:role/ClaimVision-*"
          }
        }
      },
      {
        Sid       = "AllowListBucketForClaimVisionRoles",
        Effect    = "Allow",
        Principal = "*",
        Action    = "s3:ListBucket",
        Resource  = local.reports_bucket_arn,
        Condition = {
          StringLike = {
            "aws:PrincipalArn" = "arn:aws:iam::${var.aws_account_id}:role/ClaimVision-*"
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket.reports_bucket]
}

# S3 Event Notification for uploaded files
resource "aws_s3_bucket_notification" "file_upload_notification" {
  bucket = aws_s3_bucket.claimvision_bucket.id
  
  lambda_function {
    lambda_function_arn = var.process_uploaded_file_lambda_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "pending/"
  }
}

# Permission for S3 to invoke Lambda
resource "aws_lambda_permission" "allow_s3_invoke_lambda" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = var.process_uploaded_file_lambda_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.claimvision_bucket.arn
}
