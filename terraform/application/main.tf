module "rds" {
  source                 = "./rds"
  env                    = var.env
  vpc_id                 = var.vpc_id
  public_subnet_1        = var.public_subnet_1
  public_subnet_2        = var.public_subnet_2
  rds_security_group_id  = var.rds_security_group_id
  db_username            = var.db_username
  db_password            = var.db_password
}




module "s3" {
  source         = "./s3"
  env            = var.env
  aws_account_id = var.aws_account_id
}

module "lambda" {
  source                 = "./lambda"
  env                    = var.env
  s3_bucket_name         = module.s3.s3_bucket_name
  rds_endpoint           = module.rds.rds_endpoint
  db_username            = var.db_username
  db_password            = var.db_password
  aws_region             = var.aws_region
}