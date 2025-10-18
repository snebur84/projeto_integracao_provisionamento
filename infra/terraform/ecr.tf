resource "aws_ecr_repository" "app" {
  name                 = "${var.environment}-${var.ecr_repo_name}"
  image_tag_mutability = "MUTABLE"
  tags                 = local.app_tags
}