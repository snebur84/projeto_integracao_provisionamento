# Outputs to consume after apply (terraform output -json)
output "mysql_service_id" {
  value = render_service.mysql.id
}

output "mysql_internal_hostname" {
  # provider attribute name might differ (internal_hostname, internal_host, hostname_internal)
  value = try(render_service.mysql.internal_hostname, "")
  description = "Internal hostname for the MySQL service (use as MYSQL_HOST)"
}

output "mongo_service_id" {
  value = render_service.mongo.id
}

output "mongodb_internal_hostname" {
  value = try(render_service.mongo.internal_hostname, "")
  description = "Internal hostname for the MongoDB service (use as MONGODB_HOST)"
}

output "app_service_id" {
  value = render_service.app.id
}

output "app_service_url" {
  # Many providers expose a 'default' or 'url' attribute for public service endpoint
  value = try(render_service.app.url, render_service.app.default_domain, "")
  description = "Public URL of the Django app service (empty until domain assigned)"
}