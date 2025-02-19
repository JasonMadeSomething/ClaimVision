output "rds_endpoint" {
  value = aws_db_instance.claimvision_db.address
}