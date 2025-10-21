resource "aws_ecr_repository" "app" {
  name                 = "${var.environment}-${var.name}"
  image_tag_mutability = "MUTABLE"
  tags                 = var.tags
}

output "repository_url" {
  value = aws_ecr_repository.app.repository_url
}