terraform {
  backend "s3" {
    bucket         = var.tfstate_bucket
    key            = "${var.name_prefix}/terraform.tfstate"
    region         = var.region
    dynamodb_table = var.tfstate_lock_table
    encrypt        = true
  }
}