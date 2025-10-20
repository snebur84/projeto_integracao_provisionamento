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

  tags = {
    Name        = "${var.name_prefix}-staging"
    Environment = "staging"
  }
}

# Use the separate aws_s3_bucket_acl resource as acl attr is deprecated.
resource "aws_s3_bucket_acl" "staging_acl" {
  bucket = aws_s3_bucket.staging.id
  acl    = "private"
}

output "staging_bucket" {
  value       = aws_s3_bucket.staging.bucket
  description = "Name of the staging S3 bucket"
}