# Example high-level resources — replace with modular resources
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "~> 4.0"

  name = "${var.environment}-vpc"
  cidr = "10.0.0.0/16"

  azs             = slice(data.aws_availability_zones.available.names, 0, 2)
  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets = ["10.0.101.0/24", "10.0.102.0/24"]
}

resource "aws_ecr_repository" "app" {
  name = "${var.environment}-app-repo"
}

# TODO: ecs cluster, task execution role, ALB, rds instance/module, security groups