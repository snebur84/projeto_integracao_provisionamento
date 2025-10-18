output "ecr_repository_url" {
  description = "URL of the created ECR repository"
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  value       = aws_ecs_cluster.this.name
}

output "ecs_service_name" {
  value       = aws_ecs_service.app.name
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.app.dns_name
}

output "rds_endpoint" {
  description = "RDS endpoint (address)"
  value       = aws_db_instance.app.address
}

output "docdb_endpoint" {
  description = "DocumentDB cluster endpoint (if created)"
  value       = var.enable_documentdb ? aws_docdb_cluster.docdb[0].endpoint : ""
  sensitive   = false
}