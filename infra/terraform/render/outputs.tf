output "project_id" {
  value       = try(render_project.project.id, "")
  description = "Render project id (if created)"
}

output "mysql_service_id" {
  value       = try(render_private_service.mysql.id, "")
  description = "ID of the MySQL private service"
}

output "mysql_internal_hostname" {
  value       = try(render_private_service.mysql.internal_hostname, "")
  description = "Internal hostname for MySQL (may be empty if attribute name differs)"
}

output "mongo_service_id" {
  value       = try(render_private_service.mongo.id, "")
  description = "ID of the Mongo private service"
}

output "mongodb_internal_hostname" {
  value       = try(render_private_service.mongo.internal_hostname, "")
  description = "Internal hostname for MongoDB (may be empty if attribute name differs)"
}

output "app_service_id" {
  value       = try(render_web_service.app.id, "")
  description = "ID of the web service"
}

output "app_public_domain" {
  value       = try(render_web_service.app.default_domain, try(render_web_service.app.url, ""))
  description = "Public domain or url of the web service (may be empty until domain assigned)"
}