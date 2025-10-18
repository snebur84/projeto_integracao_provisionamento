resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.environment}-${var.container_name}"
  retention_in_days = 14
  tags              = local.app_tags
}