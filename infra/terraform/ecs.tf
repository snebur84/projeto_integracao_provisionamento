# ECS cluster
resource "aws_ecs_cluster" "this" {
  name = var.ecs_cluster_name
  tags = local.app_tags
}

# Task definition (Fargate)
resource "aws_ecs_task_definition" "app" {
  family                   = "${local.name_prefix}-${var.container_name}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = templatefile("${path.module}/templates/container-definitions.json.tpl", {
    container_name = var.container_name
    image          = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
    container_port  = var.container_port
    rds_endpoint    = aws_db_instance.app.address
    log_group_name  = aws_cloudwatch_log_group.ecs.name
    aws_region      = var.aws_region
  })
}

# ECS service attached to ALB
resource "aws_ecs_service" "app" {
  name            = var.service_name
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [aws_security_group.ecs_tasks_sg.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = var.container_name
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.frontend]
  tags = local.app_tags
}