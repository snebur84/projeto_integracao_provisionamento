variable "name_prefix" {
  description = "Prefix used for resource names"
  type        = string
  default     = "provisioning"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "staging" {
  bucket = "${var.name_prefix}-staging-${random_id.bucket_suffix.hex}"
  acl    = "private"

  tags = {
    Name        = "${var.name_prefix}-staging"
    Environment = "staging"
  }
}

output "staging_bucket" {
  value = aws_s3_bucket.staging.bucket
  description = "Name of the staging S3 bucket"
}