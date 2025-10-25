terraform {
  required_version = ">= 1.1.0"

  required_providers {
    render = {
      source  = "renderapp/render"
      version = ">= 0.10.0"
    }
  }
}

provider "render" {
  api_key = var.render_api_key
}