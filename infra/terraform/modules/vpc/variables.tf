variable "environment" { type = string }
variable "vpc_cidr" { type = string, default = "10.0.0.0/16" }
variable "public_subnets" { type = list(string) }
variable "private_subnets" { type = list(string) }
variable "tags" { type = map(string) }