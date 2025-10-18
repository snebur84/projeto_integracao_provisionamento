variable "environment" { type = string }
variable "cluster_name" { type = string, default = "app-cluster" }
variable "service_name" { type = string }
variable "container_name" { type = string }
variable "container_port" { type = number }
variable "image" { type = string }
variable "task_cpu" { type = string, default = "512" }
variable "task_memory" { type = string, default = "1024" }
variable "desired_count" { type = number, default = 1 }
variable "private_subnets" { type = list(string) }
variable "security_groups" { type = list(string) }
variable "rds_endpoint" { type = string, default = "" }
variable "aws_region" { type = string }
variable "tags" { type = map(string) }