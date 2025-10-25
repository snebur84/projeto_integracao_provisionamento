terraform {
  required_version = ">= 1.1.0"

  required_providers {
    render = {
      source  = "render-oss/render"
    }
  }
}

provider "render" {
  api_key = var.render_api_key
}