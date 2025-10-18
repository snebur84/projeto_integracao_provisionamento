terraform {
  backend "s3" {
    bucket         = var.tf_state_s3_bucket
    key            = "${var.environment}/terraform.tfstate"
    region         = var.aws_region
    dynamodb_table = var.tf_lock_table
    encrypt        = true
  }
}