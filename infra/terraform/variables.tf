variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "tf_state_s3_bucket" {
  type = string
}

variable "tf_lock_table" {
  type = string
}

variable "ecr_repo_name" {
  type    = string
  default = "app-repo"
}

# DB secrets: DO NOT hardcode; set via CI/GitHub Secrets or Secrets Manager
variable "db_username" {
  type    = string
  default = "admin"
}
variable "db_password" {
  type      = string
  sensitive = true
}

# App / ECS related
variable "ecs_cluster_name" {
  type    = string
  default = "app-cluster"
}
variable "service_name" {
  type    = string
  default = "app-service"
}
variable "container_name" {
  type    = string
  default = "app"
}
variable "container_port" {
  type    = number
  default = 8000
}