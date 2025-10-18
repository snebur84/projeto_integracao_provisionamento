# ECS cluster
resource "aws_ecs_cluster" "this" {
  name = var.cluster_name
  tags = var.tags
}

# CloudWatch Log Group for tasks
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.environment}-${var.service_name}"
  retention_in_days = 14
  tags              = var.tags
}

# Task execution role (minimal)
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.environment}-${var.service_name}-task-exec-role"

  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_assume_role.json
  tags = var.tags
}

data "aws_iam_policy_document" "ecs_task_execution_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task role used by application (optional extra permissions attached by operator)
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.environment}-${var.service_name}-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_role_assume_role.json
  tags = var.tags
}

data "aws_iam_policy_document" "ecs_task_role_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Task definition using templatefile for container definitions
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.environment}-${var.service_name}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = templatefile("${path.module}/../templates/container-definitions.json.tpl", {
    container_name = var.container_name
    image          = var.image
    container_port = var.container_port
    rds_endpoint   = var.rds_endpoint
    log_group_name = aws_cloudwatch_log_group.ecs.name
    aws_region     = var.aws_region
  })
}

# ECS Service (Fargate) - assumes ALB target group is created externally or in higher-level module
resource "aws_ecs_service" "app" {
  name            = var.service_name
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnets
    security_groups = var.security_groups
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200
  tags = var.tags
}

output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "service_name" {
  value = aws_ecs_service.app.name
}

output "task_definition_arn" {
  value = aws_ecs_task_definition.app.arn
}