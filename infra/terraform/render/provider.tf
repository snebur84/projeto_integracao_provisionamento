terraform {
  required_version = ">= 1.1.0"

  required_providers {
    render = {
      source  = "render-oss/render"
      version = ">= 0.6.0"
    }
  }
}

provider "render" {
  # provider reads API key from var.render_api_key (declared abaixo).
  api_key                     = var.render_api_key
  owner_id                    = var.render_owner_id
  wait_for_deploy_completion  = var.wait_for_deploy_completion
  skip_deploy_after_service_update = var.skip_deploy_after_service_update
}