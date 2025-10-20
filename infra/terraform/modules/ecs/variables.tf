variable "cluster_name" {
  type    = string
  default = "app-cluster"
}

variable "task_cpu" {
  type    = string
  default = "512"
}

variable "task_memory" {
  type    = string
  default = "1024"
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "rds_endpoint" {
  type    = string
  default = ""
}
