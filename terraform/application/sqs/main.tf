resource "aws_sqs_queue" "file_upload_queue" {
  name                      = "claimvision-file-upload-queue-${var.env}"
  delay_seconds             = 0
  max_message_size          = 262144  # 256 KB
  message_retention_seconds = 86400   # 1 day
  receive_wait_time_seconds = 10
  visibility_timeout_seconds = 300    # 5 minutes

  tags = {
    Name = "ClaimVision-FileUploadQueue-${var.env}"
  }
}

resource "aws_sqs_queue" "file_analysis_queue" {
  name                      = "claimvision-file-analysis-queue-${var.env}"
  delay_seconds             = 0
  max_message_size          = 262144  # 256 KB
  message_retention_seconds = 86400   # 1 day
  receive_wait_time_seconds = 10
  visibility_timeout_seconds = 600    # 10 minutes

  tags = {
    Name = "ClaimVision-FileAnalysisQueue-${var.env}"
  }
}

# Dead Letter Queue for file upload processing
resource "aws_sqs_queue" "file_upload_dlq" {
  name                      = "claimvision-file-upload-dlq-${var.env}"
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name = "ClaimVision-FileUploadDLQ-${var.env}"
  }
}

# Dead Letter Queue for file analysis processing
resource "aws_sqs_queue" "file_analysis_dlq" {
  name                      = "claimvision-file-analysis-dlq-${var.env}"
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name = "ClaimVision-FileAnalysisDLQ-${var.env}"
  }
}

# Update the main queues to use the DLQs
resource "aws_sqs_queue_redrive_policy" "file_upload_redrive" {
  queue_url = aws_sqs_queue.file_upload_queue.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.file_upload_dlq.arn
    maxReceiveCount     = 5
  })
}

resource "aws_sqs_queue_redrive_policy" "file_analysis_redrive" {
  queue_url = aws_sqs_queue.file_analysis_queue.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.file_analysis_dlq.arn
    maxReceiveCount     = 5
  })
}

# User Registration Queue
resource "aws_sqs_queue" "user_registration_queue" {
  name                       = "claimvision-user-registration-queue"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 345600 # 4 days
  visibility_timeout_seconds = 60
  receive_wait_time_seconds  = 10
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.user_registration_dlq.arn
    maxReceiveCount     = 5
  })
  tags = {
    Environment = var.environment
  }
}

resource "aws_sqs_queue" "user_registration_dlq" {
  name                       = "claimvision-user-registration-dlq"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600 # 14 days
  visibility_timeout_seconds = 60
  receive_wait_time_seconds  = 10
  tags = {
    Environment = var.environment
  }
}

# Cognito Update Queue
resource "aws_sqs_queue" "cognito_update_queue" {
  name                       = "claimvision-cognito-update-queue"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 345600 # 4 days
  visibility_timeout_seconds = 60
  receive_wait_time_seconds  = 10
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.cognito_update_dlq.arn
    maxReceiveCount     = 5
  })
  tags = {
    Environment = var.environment
  }
}

resource "aws_sqs_queue" "cognito_update_dlq" {
  name                       = "claimvision-cognito-update-dlq"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600 # 14 days
  visibility_timeout_seconds = 60
  receive_wait_time_seconds  = 10
  tags = {
    Environment = var.environment
  }
}

# Report Request Queue
resource "aws_sqs_queue" "report_request_queue" {
  name                      = "claimvision-report-request-queue-${var.env}"
  delay_seconds             = 0
  max_message_size          = 262144  # 256 KB
  message_retention_seconds = 86400   # 1 day
  receive_wait_time_seconds = 10
  visibility_timeout_seconds = 300    # 5 minutes

  tags = {
    Name = "ClaimVision-ReportRequestQueue-${var.env}"
  }
}

# Report Request DLQ
resource "aws_sqs_queue" "report_request_dlq" {
  name                      = "claimvision-report-request-dlq-${var.env}"
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name = "ClaimVision-ReportRequestDLQ-${var.env}"
  }
}

# File Organization Queue
resource "aws_sqs_queue" "file_organization_queue" {
  name                      = "claimvision-file-organization-queue-${var.env}"
  delay_seconds             = 0
  max_message_size          = 262144  # 256 KB
  message_retention_seconds = 86400   # 1 day
  receive_wait_time_seconds = 10
  visibility_timeout_seconds = 600    # 10 minutes

  tags = {
    Name = "ClaimVision-FileOrganizationQueue-${var.env}"
  }
}

# File Organization DLQ
resource "aws_sqs_queue" "file_organization_dlq" {
  name                      = "claimvision-file-organization-dlq-${var.env}"
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name = "ClaimVision-FileOrganizationDLQ-${var.env}"
  }
}

# Set up redrive policies
resource "aws_sqs_queue_redrive_policy" "report_request_redrive" {
  queue_url = aws_sqs_queue.report_request_queue.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.report_request_dlq.arn
    maxReceiveCount     = 5
  })
}

resource "aws_sqs_queue_redrive_policy" "file_organization_redrive" {
  queue_url = aws_sqs_queue.file_organization_queue.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.file_organization_dlq.arn
    maxReceiveCount     = 5
  })
}

resource "aws_sqs_queue" "deliver_report_queue" {
  name = "claimvision-deliver-report-queue-${var.env}"

  message_retention_seconds = 86400  # 1 day
  visibility_timeout_seconds = 600   # 10 minutes

  tags = {
    Name = "ClaimVision-DeliverReportQueue-${var.env}"
  }
}

resource "aws_sqs_queue" "deliver_report_dlq" {
  name                      = "claimvision-deliver-report-dlq-${var.env}"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue_redrive_policy" "deliver_report_redrive" {
  queue_url = aws_sqs_queue.deliver_report_queue.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.deliver_report_dlq.arn
    maxReceiveCount     = 5
  })
}

resource "aws_sqs_queue" "email_queue" {
  name                      = "claimvision-email-queue-${var.env}"
  delay_seconds             = 0
  max_message_size          = 262144
  message_retention_seconds = 345600  # 4 days
  receive_wait_time_seconds = 0
  visibility_timeout_seconds = 30

  tags = {
    Name        = "ClaimVision Email Queue"
    Environment = var.env
  }
}

# S3 upload notification queue
resource "aws_sqs_queue" "s3_upload_notification_queue" {
  name                      = "claimvision-s3-upload-notification-queue-${var.env}"
  delay_seconds             = 0
  max_message_size          = 262144  # 256 KB
  message_retention_seconds = 86400   # 1 day
  receive_wait_time_seconds = 10
  visibility_timeout_seconds = 300    # 5 minutes

  tags = {
    Name = "ClaimVision-S3UploadNotificationQueue-${var.env}"
  }
}

# Dead Letter Queue for S3 upload notifications
resource "aws_sqs_queue" "s3_upload_notification_dlq" {
  name                      = "claimvision-s3-upload-notification-dlq-${var.env}"
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name = "ClaimVision-S3UploadNotificationDLQ-${var.env}"
  }
}

# Update the S3 notification queue to use the DLQ
resource "aws_sqs_queue_redrive_policy" "s3_upload_notification_redrive" {
  queue_url = aws_sqs_queue.s3_upload_notification_queue.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.s3_upload_notification_dlq.arn
    maxReceiveCount     = 5
  })
}

# S3 bucket notification to SQS
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = var.s3_bucket_id
  
  queue {
    queue_arn     = aws_sqs_queue.s3_upload_notification_queue.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "pending/"
  }
}

# Allow S3 to send messages to SQS
resource "aws_sqs_queue_policy" "s3_to_sqs_policy" {
  queue_url = aws_sqs_queue.s3_upload_notification_queue.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "s3.amazonaws.com"
        },
        Action = "sqs:SendMessage",
        Resource = aws_sqs_queue.s3_upload_notification_queue.arn,
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = var.s3_bucket_arn
          }
        }
      }
    ]
  })
}