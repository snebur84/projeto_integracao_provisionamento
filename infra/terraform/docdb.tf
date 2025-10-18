# Optional DocumentDB resources (create only if enable_documentdb true)
resource "aws_docdb_subnet_group" "docdb" {
  count      = var.enable_documentdb ? 1 : 0
  name       = "${local.name_prefix}-docdb-subnet-group"
  subnet_ids = module.vpc.private_subnets
  tags       = local.app_tags
}

resource "aws_docdb_cluster" "docdb" {
  count                    = var.enable_documentdb ? 1 : 0
  cluster_identifier       = "${local.name_prefix}-docdb-cluster"
  master_username          = var.docdb_username
  master_password          = var.docdb_password
  backup_retention_period  = 5
  preferred_backup_window  = "07:00-09:00"
  db_subnet_group_name     = aws_docdb_subnet_group.docdb[0].name
  vpc_security_group_ids   = var.enable_documentdb ? [aws_security_group.docdb_sg[0].id] : []
  tags                     = local.app_tags
}

resource "aws_docdb_cluster_instance" "docdb_instances" {
  count               = var.enable_documentdb ? 1 : 0
  identifier          = "${local.name_prefix}-docdb-instance-${count.index + 1}"
  cluster_identifier  = aws_docdb_cluster.docdb[0].id
  instance_class      = "db.r5.large"
  engine              = "docdb"
  engine_version      = "4.0.0"
  tags                = local.app_tags
}