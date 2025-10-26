# Exemplo ilustrativo: condicionalmente criar o serviço (ajuste o bloco ao seu módulo/provider)
resource "render_service" "provision_service" {
  count = var.create_service ? 1 : 0

  name = var.service_name
  # outros atributos do serviço web (type, repo, branch, env, build_command, start_command ...)
  # ...
}

# Exemplo: criar Postgres no Render (se você optar por criar via TF)
resource "render_database" "postgres" {
  count = var.create_postgres ? 1 : 0

  name     = var.postgres_database
  region   = "oregon" # exemplo
  plan     = "starter" # ajuste conforme necessidade
  # se o provider/module permitir, exponha a connection string em um output
}

# Outputs: exponha id do serviço e conexão do Postgres (nome das saídas depende dos recursos usados)
output "provision_service_id" {
  value       = length(render_service.provision_service) > 0 ? render_service.provision_service[0].id : ""
  description = "ID do serviço Render para a aplicação provision (vazia se serviço não criado por este TF run)"
}

output "postgres_database_url" {
  value       = length(render_database.postgres) > 0 ? render_database.postgres[0].connection_string : ""
  description = "Connection string para o Postgres criado (se aplicável)"
}