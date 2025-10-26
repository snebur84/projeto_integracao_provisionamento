# infra/terraform/render/outputs.tf
# Saídas úteis para o workflow: ids de projeto/serviços criados (vazias caso o recurso não tenha sido criado por este run).

output "project_id" {
  description = "ID do projeto Render criado/gerenciado por este módulo (vazio se não criado aqui)."
  value       = try(render_project.project.id, "")
}

output "project_environments" {
  description = "Map de environments do projeto (vazio se não criado aqui)."
  value       = try(render_project.project.environments, {})
}

output "provision_service_id" {
  description = "ID do serviço web (Django) criado (vazio se var.create_service=false ou se não criado por este run)."
  value       = length(render_web_service.provision) > 0 ? render_web_service.provision[0].id : ""
}

output "provision_service_name" {
  description = "Nome do serviço web (Django) correspondente."
  value       = length(render_web_service.provision) > 0 ? render_web_service.provision[0].name : ""
}

output "postgres_database_url" {
  description = "Connection string do Postgres gerenciado (sensible)."
  value       = try(render_database.postgres[0].connection_string, "")
  sensitive   = true
}