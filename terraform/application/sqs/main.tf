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
