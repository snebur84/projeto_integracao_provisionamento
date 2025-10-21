[
  {
    "name": "${container_name}",
    "image": "${image}",
    "portMappings": [
      {
        "containerPort": ${container_port},
        "protocol": "tcp"
      }
    ],
    "essential": true,
    "environment": [
      {
        "name": "DATABASE_HOST",
        "value": "${rds_endpoint}"
      }
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "${log_group_name}",
        "awslogs-region": "${aws_region}",
        "awslogs-stream-prefix": "${container_name}"
      }
    }
  }
]