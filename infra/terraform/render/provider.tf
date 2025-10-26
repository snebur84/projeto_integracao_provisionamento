# Provider configuration: use o provider oficial do Render (verifique a versão no Terraform Registry)
terraform {
  required_providers {
    # Atenção: confirme no Terraform Registry qual o "source" correto (ex.: "render/render").
    # Se o provider no seu código atual for outro (ex.: "render-oss/render"), verifique a documentação
    # desse provider e ajuste os tipos de recurso conforme o provider escolhido.
    render = {
      source  = "render-oss/render"
      version = ">= 0.6.0"
    }
  }

  required_version = ">= 1.0.0"
}

provider "render" {
  # O provider oficial aceita a api_key via configuração ou via env var RENDER_API_KEY
  api_key  = var.render_api_key
  owner_id = var.render_owner_id
}