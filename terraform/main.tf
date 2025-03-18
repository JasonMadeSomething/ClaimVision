provider "aws" {
  region = var.aws_region
}

terraform {
  backend "s3" {
    bucket         = "claimvision-terraform-state"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "claimvision-terraform-lock"
  }
}

# Deploy Networking First
module "networking" {
  source   = "./networking"
  env      = var.env
  vpc_cidr = var.vpc_cidr
  public_ip = var.public_ip
}

# Deploy Application (Depends on Networking)
module "application" {
  source               = "./application"
  env                  = var.env
  vpc_id               = module.networking.vpc_id
  public_subnet_1      = module.networking.public_subnet_1
  public_subnet_2      = module.networking.public_subnet_2
  rds_security_group_id = module.networking.rds_security_group_id
  db_username          = var.db_username
  db_password          = var.db_password
  aws_account_id       = data.aws_caller_identity.current.account_id
  aws_region           = var.aws_region
}

# Deploy SSM Parameters (Depends on Application)
module "ssm" {
  source = "./application/ssm"
  db_username = var.db_username
  env = var.env
  public_subnet_1       = module.networking.public_subnet_1
  public_subnet_2       = module.networking.public_subnet_2
  rds_security_group_id = module.networking.rds_security_group_id
  db_password           = var.db_password
  rds_endpoint          = module.application.rds_endpoint
  s3_bucket_name        = module.application.s3_bucket_name
}

data "aws_caller_identity" "current" {}

locals {
  aws_account_id = data.aws_caller_identity.current.account_id
}