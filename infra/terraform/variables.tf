variable "public_key" {
  description = "Public SSH key to add as aws_key_pair (ssh-rsa or ssh-ed25519). Optional if using SSM only."
  type        = string
  default     = ""
  sensitive   = true
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "root_volume_size" {
  description = "Root volume size in GB"
  type        = number
  default     = 30
}

variable "associate_public_ip" {
  description = "Whether to associate a public IP"
  type        = bool
  default     = true
}

variable "allowed_cidrs" {
  description = "List of CIDR blocks allowed for SSH/HTTP access"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "vpc_id" {
  description = "Optional VPC id. Leave empty to use default."
  type        = string
  default     = ""
}

variable "subnet_id" {
  description = "Optional subnet id. Leave empty to use default."
  type        = string
  default     = ""
}

variable "s3_bucket" {
  description = "S3 bucket name used by CI to stage artifacts (will create if empty)"
  type        = string
  default     = ""
}

variable "tfstate_bucket" {
  description = "S3 bucket used for Terraform state backend"
  type        = string
  default     = ""
}

variable "tfstate_lock_table" {
  description = "DynamoDB table name used for Terraform state locking"
  type        = string
  default     = ""
}