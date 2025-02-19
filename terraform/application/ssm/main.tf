resource "aws_ssm_parameter" "public_subnet_1" {
  name  = "/terraform/networking/public_subnet_1"
  type  = "String"
  value = var.public_subnet_1  # ✅ Uses a variable instead of aws_subnet reference
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "public_subnet_2" {
  name  = "/terraform/networking/public_subnet_2"
  type  = "String"
  value = var.public_subnet_2  # ✅ Uses a variable instead of aws_subnet reference
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "rds_security_group_id" {
  name  = "/terraform/networking/rds_sg_id"
  type  = "String"
  value = var.rds_security_group_id  # ✅ Uses a variable instead of aws_security_group reference
  lifecycle {
    ignore_changes = [value]
  }
}


resource "aws_secretsmanager_secret" "db_secret" {
  name        = "ClaimVisionDBPassword"
  description = "Stores database credentials for ClaimVision"
}

resource "aws_secretsmanager_secret_version" "db_secret_version" {
  secret_id     = aws_secretsmanager_secret.db_secret.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
  })
}

resource "aws_ssm_parameter" "db_password" {
  name  = "/terraform/application/db_password"
  type  = "SecureString"
  value = var.db_password
  lifecycle {
    ignore_changes = [value]
  }
}

output "db_password" {
  value = var.db_password
  sensitive = true
}
