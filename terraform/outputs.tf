# ✅ Networking Outputs
output "vpc_id" {
  value = module.networking.vpc_id
}

output "public_subnet_1" {
  value = module.networking.public_subnet_1
}

output "public_subnet_2" {
  value = module.networking.public_subnet_2
}

output "rds_security_group_id" {
  value = module.networking.rds_security_group_id
}

# ✅ Application Outputs
output "rds_endpoint" {
  value = module.application.rds_endpoint
}

output "s3_bucket_name" {
  value = module.application.s3_bucket_name
}
