# Provider configuration para Render (usando source = "render/render")
# Ajuste o version constraint se quiser fixar uma versão específica.
terraform {
  required_version = ">= 1.1.0"

  required_providers {
    render = {
      source  = "render/render"
      version = ">= 0.10.0"
    }
  }
}

provider "render" {
  # Pode receber a chave via variável (TF_VAR_render_api_key) ou via env RENDER_API_KEY.
  # O workflow que criamos já exporta TF_VAR_render_api_key a partir do secret RENDER_API_KEY.
  api_key = var.render_api_key

  # Opcional: se o provider suportar region ou outros parâmetros, adicione aqui.
  # region = var.region
}