output "instance_id" {
  value = aws_instance.provision.id
}

output "public_ip" {
  value = aws_instance.provision.public_ip
}

output "public_dns" {
  value = aws_instance.provision.public_dns
}

output "instance_profile" {
  value = aws_iam_instance_profile.ec2_profile.name
}

output "staging_bucket" {
  value = local.staging_bucket
}