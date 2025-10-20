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

variable "name_prefix" {
  description = "Prefix used for resource names"
  type        = string
  default     = "meuprojeto"
}

# Find a recent Ubuntu AMI (adjust filter if you prefer another distro)
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

# IAM role for EC2 to allow SSM + S3 read (created only if instance)
resource "aws_iam_role" "ec2_role" {
  count = var.create_instance ? 1 : 0

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

# Attach SSM managed policy so SSM can manage the instance
resource "aws_iam_role_policy_attachment" "ssm_attach" {
  count      = var.create_instance ? 1 : 0
  role       = aws_iam_role.ec2_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Attach S3 read-only so the instance can download the provisioning script
# (This is broad read-only; you can replace with a tighter inline policy
# scoped to your bucket ARN if you prefer.)
resource "aws_iam_role_policy_attachment" "s3_read_attach" {
  count      = var.create_instance ? 1 : 0
  role       = aws_iam_role.ec2_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  count = var.create_instance ? 1 : 0
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

  # Use instance profile created above (or null when not creating)
  iam_instance_profile = var.create_instance ? aws_iam_instance_profile.ec2_profile[0].name : null

  # Security groups: only set if provided
  vpc_security_group_ids = length(var.sg_ids) > 0 ? var.sg_ids : null

  tags = {
    Name = "${var.name_prefix}-provision"
  }
}