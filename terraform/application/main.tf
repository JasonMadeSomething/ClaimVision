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

module "sqs" {
  source        = "./sqs"
  env           = var.env
  environment   = var.env
  s3_bucket_id  = module.s3.s3_bucket_id
  s3_bucket_arn = module.s3.s3_bucket_arn
}

module "s3" {
  source         = "./s3"
  env            = var.env
  aws_account_id = var.aws_account_id
}

module "ssm" {
  source              = "./ssm"
  env                 = var.env
  db_username         = var.db_username
  db_password         = var.db_password
  public_subnet_1     = var.public_subnet_1
  public_subnet_2     = var.public_subnet_2
  rds_security_group_id = var.rds_security_group_id
  rds_endpoint        = module.rds.rds_endpoint
  s3_bucket_name      = module.s3.s3_bucket_name
}

module "efs" {
  source                 = "./efs"
  env                    = var.env
  vpc_id                 = var.vpc_id
  public_subnet_1        = var.public_subnet_1
  public_subnet_2        = var.public_subnet_2
  lambda_security_group_id = var.lambda_security_group_id
}

module "ses" {
  source      = "./ses"
  env         = var.env
  domain_name = var.domain_name
  sender_email = var.sender_email
}