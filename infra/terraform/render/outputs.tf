output "project_id" {
  value       = try(render_project.project.id, "")
  description = "Render project id"
}

output "project_environments" {
  value       = try(render_project.project.environments, {})
  description = "Map of created environments on the project"
}

output "mysql_service_id" {
  value       = try(render_private_service.mysql.id, "")
  description = "ID of the MySQL private service"
}

output "mysql_service_url" {
  value       = try(render_private_service.mysql.url, "")
  description = "URL (internal/external) for the MySQL service"
}

output "mongo_service_id" {
  value       = try(render_private_service.mongo.id, "")
  description = "ID of the MongoDB private service"
}

output "mongo_service_url" {
  value       = try(render_private_service.mongo.url, "")
  description = "URL for the MongoDB service"
}

output "app_service_id" {
  value       = try(render_web_service.app.id, "")
  description = "ID of the web service"
}

output "app_public_url" {
  value       = try(render_web_service.app.url, "")
  description = "Public URL of the web app (empty until assigned)"
}