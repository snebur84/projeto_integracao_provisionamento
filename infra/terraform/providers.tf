provider "aws" {
  region = var.aws_region
  # Optionally allow assuming a role:
  # assume_role {
  #   role_arn = var.assume_role_arn
  # }
}