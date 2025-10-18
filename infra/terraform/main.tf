locals {
  name_prefix = "${var.environment}"
  app_tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Project     = "projeto_integracao_provisionamento"
  }
}

# VPC module
module "vpc" {
  source = "./modules/vpc"
  environment = var.environment
  # passe overrides (cidr, subnets) conforme necessário
}

# ECR module
module "ecr" {
  source = "./modules/ecr"
  environment = var.environment
  name = var.ecr_repo_name
  tags = local.app_tags
}

# ECS + ALB + RDS: use módulo ecs que referencia module.vpc, module.ecr, etc.
module "ecs" {
  source = "./modules/ecs"
  environment     = var.environment
  container_name  = var.container_name
  container_port  = var.container_port
  ecr_repository  = module.ecr.repository_url
  vpc_id          = module.vpc.vpc_id
  private_subnets = module.vpc.private_subnets
  public_subnets  = module.vpc.public_subnets
  tags            = local.app_tags
}