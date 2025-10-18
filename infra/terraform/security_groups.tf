# ALB security group
resource "aws_security_group" "alb_sg" {
  name        = "${local.name_prefix}-alb-sg"
  description = "Allow inbound HTTP from anywhere to ALB"
  vpc_id      = module.vpc.vpc_id
  tags        = merge(local.app_tags, { Name = "${local.name_prefix}-alb-sg" })

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ECS tasks security group
resource "aws_security_group" "ecs_tasks_sg" {
  name        = "${local.name_prefix}-ecs-tasks-sg"
  description = "Allow traffic from ALB and outbound to DB"
  vpc_id      = module.vpc.vpc_id
  tags        = merge(local.app_tags, { Name = "${local.name_prefix}-ecs-tasks-sg" })

  ingress {
    description = "From ALB"
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# RDS security group (private)
resource "aws_security_group" "rds_sg" {
  name        = "${local.name_prefix}-rds-sg"
  description = "Allow MySQL from ECS tasks"
  vpc_id      = module.vpc.vpc_id
  tags        = merge(local.app_tags, { Name = "${local.name_prefix}-rds-sg" })

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks_sg.id]
    description     = "Allow MySQL from ECS tasks"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# DocumentDB security group (if enabled)
resource "aws_security_group" "docdb_sg" {
  count       = var.enable_documentdb ? 1 : 0
  name        = "${local.name_prefix}-docdb-sg"
  description = "Allow DocumentDB from ECS tasks"
  vpc_id      = module.vpc.vpc_id
  tags        = merge(local.app_tags, { Name = "${local.name_prefix}-docdb-sg" })

  ingress {
    from_port       = 27017
    to_port         = 27017
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks_sg.id]
    description     = "Allow DocumentDB from ECS tasks"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}