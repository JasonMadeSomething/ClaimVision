### ✅ Define all Lambda Functions in a Map
variable "lambda_functions" {
  type = map(object({
    path    = string
    handler = string
  }))
  default = {
    "upload_file" = {
      path    = "../../../src/files/upload_file.py"
      handler = "upload_file.lambda_handler"
    },
    "get_file" = {
      path    = "../../../src/files/get_file.py"
      handler = "get_file.lambda_handler"
    }
  }
}

### ✅ Automatically Package & Deploy Each Lambda Function
resource "aws_lambda_function" "lambda" {
  for_each        = var.lambda_functions
  function_name   = "ClaimVision-${each.key}-${var.env}"
  role            = aws_iam_role.lambda_exec.arn
  handler         = each.value.handler
  runtime         = "python3.12"

  ### ✅ Package Each Lambda Separately
  filename         = "${path.module}/${each.key}.zip"
  source_code_hash = filebase64sha256("${path.module}/${each.key}.zip")

  environment {
    variables = {
      DATABASE_HOST     = var.rds_endpoint
      DATABASE_NAME     = "claimvision"
      DATABASE_USER     = var.db_username
      DATABASE_PASSWORD = var.db_password
      S3_BUCKET_NAME    = var.s3_bucket_name
    }
  }

  tags = {
    Name = "ClaimVision-${each.key}-${var.env}"
  }
}

### ✅ Archive Files for Each Lambda Function
data "archive_file" "lambda_zip" {
  for_each   = var.lambda_functions
  type       = "zip"
  source_file = "${path.module}/${each.value.path}"
  output_path = "${path.module}/${each.key}.zip"
}

### ✅ IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_exec" {
  name = "ClaimVisionLambdaExecutionRole-${var.env}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

### ✅ Attach Basic Lambda Execution Policy
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_exec.name
}

### ✅ IAM Policy to Allow Lambda to Write to S3
resource "aws_iam_policy" "lambda_s3_access" {
  name        = "ClaimVisionLambdaS3Access-${var.env}"
  description = "Allows Lambda to upload files to S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:PutObject"]
        Resource = "arn:aws:s3:::${var.s3_bucket_name}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3_access_attach" {
  policy_arn = aws_iam_policy.lambda_s3_access.arn
  role       = aws_iam_role.lambda_exec.name
}

### ✅ IAM Policy to Allow Lambda to Connect to RDS
resource "aws_iam_policy" "lambda_rds_access" {
  name        = "ClaimVisionLambdaRDSAccess-${var.env}"
  description = "Allows Lambda to connect to RDS"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["rds-db:connect"]
       Resource = "arn:aws:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:db:claimvision-${var.env}"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_rds_access_attach" {
  policy_arn = aws_iam_policy.lambda_rds_access.arn
  role       = aws_iam_role.lambda_exec.name
}

data "aws_caller_identity" "current" {}
