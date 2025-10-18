# Crie aqui:
# - aws_ecs_cluster
# - aws_iam_role (exec & task role)
# - aws_cloudwatch_log_group
# - aws_ecs_task_definition (use templatefile + templates/container-definitions.json.tpl)
# - aws_lb, aws_lb_target_group, aws_lb_listener (ou export ALB em módulo separado)
# - aws_ecs_service (Fargate), associando target_group e network configuration (private subnets)
#
# Use variables for image tag, desired_count, cpu/memory.