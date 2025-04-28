resource "aws_ssm_parameter" "public_subnet_1" {
  name  = "/terraform/networking/public_subnet_1"
  type  = "String"
  value = var.public_subnet_1  # ✅ Uses a variable instead of aws_subnet reference
  overwrite = true
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "public_subnet_2" {
  name  = "/terraform/networking/public_subnet_2"
  type  = "String"
  value = var.public_subnet_2  # ✅ Uses a variable instead of aws_subnet reference
  overwrite = true
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "rds_security_group_id" {
  name  = "/terraform/networking/rds_sg_id"
  type  = "String"
  value = var.rds_security_group_id  # ✅ Uses a variable instead of aws_security_group reference
  overwrite = true
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "db_password" {
  name  = "/terraform/database/password"
  type  = "SecureString"
  value = var.db_password
  overwrite = true
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "db_username" {
  name  = "/terraform/database/username"
  type  = "String"
  value = var.db_username
  overwrite = true
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "db_host" {
  name  = "/terraform/database/host"
  type  = "String"
  value = var.rds_endpoint
  overwrite = true
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "s3_bucket_name" {
  name  = "/terraform/s3/bucket_name"
  type  = "String"
  value = var.s3_bucket_name
  overwrite = true
  lifecycle {
    ignore_changes = [value]
  }
}

output "db_password" {
  value = var.db_password
  sensitive = true
}
