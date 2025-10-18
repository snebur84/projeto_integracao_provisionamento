provider "aws" {
  region = var.aws_region

  # Optional: assume role via TF var if you use OIDC / cross-account
  # assume_role {
  #   role_arn = var.assume_role_arn
  # }
}