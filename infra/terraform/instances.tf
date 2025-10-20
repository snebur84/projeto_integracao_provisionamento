# EC2 / IAM / SSM resources for provisioning VM
# The instance and IAM resources are created only when create_instance = true.

variable "create_instance" {
  description = "Create an EC2 instance for provisioning?"
  type        = bool
  default     = true
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

variable "existing_instance_profile" {
  description = "Name of an existing IAM instance profile to use (optional)"
  type        = string
  default     = ""
}

locals {
  use_existing_profile = length(trimspace(var.existing_instance_profile)) > 0
}

# If user provided an existing profile name, read it; otherwise count=0.
data "aws_iam_instance_profile" "existing" {
  count = local.use_existing_profile ? 1 : 0
  name  = var.existing_instance_profile
}

# Only create role/profile/attachments when creating instance AND not using
# an existing profile. This avoids requiring iam:CreateRole permissions
# when the runner/account can't create IAM resources.
resource "aws_iam_role" "ec2_role" {
  count = (var.create_instance && !local.use_existing_profile) ? 1 : 0

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
  count      = (var.create_instance && !local.use_existing_profile) ? 1 : 0
  role       = aws_iam_role.ec2_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "s3_read_attach" {
  count      = (var.create_instance && !local.use_existing_profile) ? 1 : 0
  role       = aws_iam_role.ec2_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  count = (var.create_instance && !local.use_existing_profile) ? 1 : 0
  name  = "${var.name_prefix}-ec2-profile"
  role  = aws_iam_role.ec2_role[0].name
}

# EC2 instance (created only when create_instance = true)
resource "aws_instance" "provision" {
  count = var.create_instance ? 1 : 0

  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = length(trimspace(var.key_name)) > 0 ? var.key_name : null
  subnet_id     = length(trimspace(var.subnet_id)) > 0 ? var.subnet_id : null

  # Single-line nested conditional expression (valid Terraform syntax)
  iam_instance_profile = local.use_existing_profile ? data.aws_iam_instance_profile.existing[0].name : (var.create_instance ? aws_iam_instance_profile.ec2_profile[0].name : null)

  vpc_security_group_ids = length(var.sg_ids) > 0 ? var.sg_ids : null

  tags = {
    Name = "${var.name_prefix}-provision"
  }
}

# Data source for Ubuntu AMI (kept at the end for readability)
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}