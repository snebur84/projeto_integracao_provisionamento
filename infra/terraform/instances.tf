# EC2 / IAM / provisioning via user_data (presigned URL)
# By default Terraform will NOT attempt to create IAM roles.
# The instance will run a provision script downloaded from a presigned URL.

variable "create_instance" {
  description = "Create an EC2 instance for provisioning?"
  type        = bool
  default     = true
}

variable "create_iam_role" {
  description = "Allow Terraform to create IAM role/profile (dangerous)."
  type        = bool
  default     = false
}

variable "existing_instance_profile" {
  description = "Name of an existing IAM instance profile to use (optional)"
  type        = string
  default     = ""
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "Optional SSH key name"
  type        = string
  default     = ""
}

variable "sg_ids" {
  description = "Optional list of security group ids"
  type        = list(string)
  default     = []
}

variable "subnet_id" {
  description = "Optional subnet id"
  type        = string
  default     = ""
}

variable "presigned_url" {
  description = "Pre-signed URL to download the provisioning script"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Environment name passed to the provision script"
  type        = string
  default     = "prod"
}

# local flags and computed name
locals {
  use_existing_profile = length(trimspace(var.existing_instance_profile)) > 0

  # single-line ternary expression to avoid HCL parsing errors caused by
  # multi-line ternary breaks. This computes the instance profile name:
  # - existing profile (data source) when provided
  # - otherwise the profile created by this module (if create_iam_role)
  # - otherwise null
  instance_profile_name = local.use_existing_profile ?
    data.aws_iam_instance_profile.existing[0].name :
    (var.create_instance && var.create_iam_role ?
      aws_iam_instance_profile.ec2_profile[0].name : null)
}

# If user provided an existing profile name, read it; otherwise count=0.
data "aws_iam_instance_profile" "existing" {
  count = local.use_existing_profile ? 1 : 0
  name  = var.existing_instance_profile
}

# Only create role/profile/attachments when explicitly allowed by
# create_iam_role and not using an existing profile.
resource "aws_iam_role" "ec2_role" {
  count = (var.create_instance && var.create_iam_role && !local.use_existing_profile) ? 1 : 0

  name = "${var.name_prefix}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_attach" {
  count      = (var.create_instance && var.create_iam_role && !local.use_existing_profile) ? 1 : 0
  role       = aws_iam_role.ec2_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "s3_read_attach" {
  count      = (var.create_instance && var.create_iam_role && !local.use_existing_profile) ? 1 : 0
  role       = aws_iam_role.ec2_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  count = (var.create_instance && var.create_iam_role && !local.use_existing_profile) ? 1 : 0
  name  = "${var.name_prefix}-ec2-profile"
  role  = aws_iam_role.ec2_role[0].name
}

# Data source for Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

# EC2 instance (created only when create_instance = true)
resource "aws_instance" "provision" {
  count = var.create_instance ? 1 : 0

  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = length(trimspace(var.key_name)) > 0 ? var.key_name : null
  subnet_id     = length(trimspace(var.subnet_id)) > 0 ? var.subnet_id : null

  # Use the computed local.instance_profile_name (single token).
  iam_instance_profile = local.instance_profile_name

  vpc_security_group_ids = length(var.sg_ids) > 0 ? var.sg_ids : null

  # user_data downloads the presigned URL (in var.presigned_url)
  # and executes the provisioning script on first boot.
  user_data = <<-EOF
    #!/bin/bash
    set -euo pipefail
    PRESIGNED_URL="${var.presigned_url}"
    ENVIRONMENT="${var.environment}"
    if [ -n "${PRESIGNED_URL}" ]; then
      echo "Downloading provision script..."
      curl -fsSL "${PRESIGNED_URL}" -o /tmp/provision.sh || exit 1
      chmod +x /tmp/provision.sh
      /bin/bash /tmp/provision.sh "${ENVIRONMENT}"
    else
      echo "No presigned URL provided; nothing to run."
    fi
  EOF

  tags = {
    Name = "${var.name_prefix}-provision"
  }
}

output "instance_id" {
  value       = try(aws_instance.provision[0].id, "")
  description = "ID of created instance (empty if not created)"
}

output "public_ip" {
  value       = try(aws_instance.provision[0].public_ip, "")
  description = "Public IP (if assigned)"
}