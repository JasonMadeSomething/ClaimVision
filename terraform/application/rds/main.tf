resource "aws_db_instance" "claimvision_db" {
  identifier              = "claimvision-${var.env}"
  engine                  = "postgres"
  instance_class          = "db.t3.micro"
  allocated_storage       = 20
  storage_encrypted       = true
  backup_retention_period = 7
  deletion_protection     = false
  publicly_accessible     = true
  username               = var.db_username
  password               = var.db_password
  vpc_security_group_ids = [var.rds_security_group_id]
  db_subnet_group_name   = aws_db_subnet_group.claimvision_db_subnet_group.name

  lifecycle {
    create_before_destroy = true
    replace_triggered_by = [
      aws_db_subnet_group.claimvision_db_subnet_group.id
    ]
    ignore_changes = [
      password,
      db_subnet_group_name
    ]
  }

  tags = {
    Name = "ClaimVisionRDS-${var.env}"
  }
}

resource "aws_db_subnet_group" "claimvision_db_subnet_group" {
  name       = "claimvision-db-subnet-group-${var.env}"
  subnet_ids = [var.public_subnet_1, var.public_subnet_2]

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "ClaimVisionDBSubnetGroup-${var.env}"
  }
}
