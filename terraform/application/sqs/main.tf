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
  name                      = "claimvision-user-registration-queue-${var.env}"
  delay_seconds             = 0
  max_message_size          = 262144  # 256 KB
  message_retention_seconds = 86400   # 1 day
  receive_wait_time_seconds = 10
  visibility_timeout_seconds = 300    # 5 minutes

  tags = {
    Name = "ClaimVision-UserRegistrationQueue-${var.env}"
  }
}

# Dead Letter Queue for user registration
resource "aws_sqs_queue" "user_registration_dlq" {
  name                      = "claimvision-user-registration-dlq-${var.env}"
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name = "ClaimVision-UserRegistrationDLQ-${var.env}"
  }
}

# Update the user registration queue to use the DLQ
resource "aws_sqs_queue_redrive_policy" "user_registration_redrive" {
  queue_url = aws_sqs_queue.user_registration_queue.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.user_registration_dlq.arn
    maxReceiveCount     = 5
  })
}
