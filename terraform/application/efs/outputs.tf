output "efs_file_system_id" {
  value = aws_efs_file_system.reports_efs.id
}

output "efs_access_point_arn" {
  value = aws_efs_access_point.reports_access_point.arn
}

output "efs_security_group_id" {
  value = aws_security_group.efs_sg.id
}

output "files_efs_file_system_id" {
  value = aws_efs_file_system.files_efs.id
}

output "files_efs_access_point_arn" {
  value = aws_efs_access_point.files_access_point.arn
}
