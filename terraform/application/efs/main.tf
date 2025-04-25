resource "aws_efs_file_system" "reports_efs" {
  creation_token = "claimvision-reports-efs-${var.env}"
  # Removed availability_zone_name to make it a regional EFS
  
  lifecycle_policy {
    transition_to_ia = "AFTER_7_DAYS" # Faster transition to save costs
  }
  
  tags = {
    Name = "ClaimVision-ReportsEFS-${var.env}"
  }
}

# Security group for EFS
resource "aws_security_group" "efs_sg" {
  name        = "claimvision-efs-sg-${var.env}"
  description = "Allow EFS access from Lambda functions"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 2049  # NFS port
    to_port     = 2049
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"] # VPC CIDR range - adjust if yours is different
    description = "Allow NFS access from within VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ClaimVision-EFS-SG-${var.env}"
  }
}

# Mount targets in each subnet
resource "aws_efs_mount_target" "reports_efs_mount_1" {
  file_system_id  = aws_efs_file_system.reports_efs.id
  subnet_id       = var.public_subnet_1
  security_groups = [aws_security_group.efs_sg.id]
}

resource "aws_efs_mount_target" "reports_efs_mount_2" {
  file_system_id  = aws_efs_file_system.reports_efs.id
  subnet_id       = var.public_subnet_2
  security_groups = [aws_security_group.efs_sg.id]
}

# Access point for Lambda functions
resource "aws_efs_access_point" "reports_access_point" {
  file_system_id = aws_efs_file_system.reports_efs.id
  
  posix_user {
    gid = 1000
    uid = 1000
  }
  
  root_directory {
    path = "/reports"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }
  
  tags = {
    Name = "ClaimVision-ReportsAccessPoint-${var.env}"
  }
}

# File Processing EFS for handling ZIP files
resource "aws_efs_file_system" "files_efs" {
  creation_token = "claimvision-files-efs-${var.env}"
  
  lifecycle_policy {
    transition_to_ia = "AFTER_7_DAYS"
  }
  
  tags = {
    Name = "ClaimVision-FilesEFS-${var.env}"
  }
}

# Mount targets for file processing EFS
resource "aws_efs_mount_target" "files_efs_mount_1" {
  file_system_id  = aws_efs_file_system.files_efs.id
  subnet_id       = var.public_subnet_1
  security_groups = [aws_security_group.efs_sg.id]
}

resource "aws_efs_mount_target" "files_efs_mount_2" {
  file_system_id  = aws_efs_file_system.files_efs.id
  subnet_id       = var.public_subnet_2
  security_groups = [aws_security_group.efs_sg.id]
}

# Access point for file processing Lambda functions
resource "aws_efs_access_point" "files_access_point" {
  file_system_id = aws_efs_file_system.files_efs.id
  
  posix_user {
    gid = 1000
    uid = 1000
  }
  
  root_directory {
    path = "/files"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }
  
  tags = {
    Name = "ClaimVision-FilesAccessPoint-${var.env}"
  }
}