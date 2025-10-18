resource "aws_db_subnet_group" "rds" {
  name       = "${local.name_prefix}-rds-subnet-group"
  subnet_ids = module.vpc.private_subnets
  tags       = local.app_tags
}

resource "aws_db_instance" "app" {
  identifier              = var.rds_instance_identifier
  allocated_storage       = var.rds_allocated_storage
  engine                  = var.rds_engine
  engine_version          = var.rds_engine_version
  instance_class          = var.rds_instance_class
  name                    = "${var.environment}_db"
  username                = var.db_username
  password                = var.db_password
  parameter_group_name    = "default.mysql8.0"
  skip_final_snapshot     = true
  publicly_accessible     = false
  multi_az                = false
  db_subnet_group_name    = aws_db_subnet_group.rds.name
  vpc_security_group_ids  = [aws_security_group.rds_sg.id]
  tags                    = local.app_tags

  # optional performance/backup settings could be added here
  deletion_protection = false
}