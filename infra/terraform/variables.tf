variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (prod/staging/dev)"
  type        = string
  default     = "prod"
}

variable "tf_state_s3_bucket" {
  description = "S3 bucket name for Terraform remote state"
  type        = string
}

variable "tf_lock_table" {
  description = "DynamoDB table name used for Terraform state locking"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnets" {
  description = "CIDRs for public subnets (list)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnets" {
  description = "CIDRs for private subnets (list)"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "ecr_repo_name" {
  description = "ECR repository name"
  type        = string
  default     = "app-repo"
}

variable "ecs_cluster_name" {
  description = "ECS cluster name"
  type        = string
  default     = "app-cluster"
}

variable "service_name" {
  description = "ECS service name"
  type        = string
  default     = "app-service"
}

variable "container_name" {
  description = "Container name used in the task definition"
  type        = string
  default     = "app"
}

variable "container_port" {
  description = "Container listening port"
  type        = number
  default     = 8000
}

variable "task_cpu" {
  description = "Task cpu units"
  type        = string
  default     = "512"
}

variable "task_memory" {
  description = "Task memory (MB)"
  type        = string
  default     = "1024"
}

variable "desired_count" {
  description = "ECS service desired count"
  type        = number
  default     = 2
}

variable "enable_documentdb" {
  description = "Whether to create Amazon DocumentDB (Mongo compatible)"
  type        = bool
  default     = false
}

variable "rds_instance_identifier" {
  description = "RDS instance identifier"
  type        = string
  default     = "app-db"
}

variable "rds_engine" {
  description = "RDS engine"
  type        = string
  default     = "mysql"
}

variable "rds_engine_version" {
  description = "RDS engine version"
  type        = string
  default     = "8.0"
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage (GB)"
  type        = number
  default     = 20
}

variable "db_username" {
  description = "Database master username (RDS)"
  type        = string
  default     = "admin"
}

variable "db_password" {
  description = "Database master password (RDS) - use secrets in CI or terraform.tfvars"
  type        = string
  sensitive   = true
}

variable "docdb_username" {
  description = "DocumentDB master username"
  type        = string
  default     = "docdbadmin"
}

variable "docdb_password" {
  description = "DocumentDB master password - use secrets"
  type        = string
  sensitive   = true
}

variable "image_tag" {
  description = "ECR image tag that the app pipeline will push and the ECS task will use"
  type        = string
  default     = "latest"
}