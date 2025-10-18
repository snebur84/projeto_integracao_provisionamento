locals {
  name_prefix = "${var.environment}"
  app_tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Project     = "projeto_integracao_provisionamento"
  }
}