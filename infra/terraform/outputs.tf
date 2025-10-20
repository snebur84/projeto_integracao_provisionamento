# Outputs guarded with try() so Terraform init/validate won't fail when no
# instance/profile was created (create_instance = false).

output "instance_id" {
  description = "ID of the provision instance (empty if not created)"
  value       = try(aws_instance.provision[0].id, "")
}

output "public_ip" {
  description = "Public IP of provision instance (empty if not created)"
  value       = try(aws_instance.provision[0].public_ip, "")
}

output "public_dns" {
  description = "Public DNS of provision instance (empty if not created)"
  value       = try(aws_instance.provision[0].public_dns, "")
}

output "instance_profile" {
  description = "Instance profile name attached to the instance"
  value       = try(aws_iam_instance_profile.ec2_profile[0].name, "")
}