# NOTE: this file is intentionally compact — adapt to your repo structure and modules as needed.

# Optionally create the staging S3 bucket if not provided
resource "aws_s3_bucket" "staging" {
  count        = var.s3_bucket == "" ? 1 : 0
  bucket       = "${var.name_prefix}-staging-${random_id.bucket_suffix.hex}"
  acl          = "private"
  force_destroy = true

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  tags = { Name = "${var.name_prefix}-staging" }
}

# random suffix used when creating bucket name
resource "random_id" "bucket_suffix" {
  count = var.s3_bucket == "" ? 1 : 0
  byte_length = 4
}

# Use either user-provided bucket or the created one
locals {
  staging_bucket = var.s3_bucket != "" ? var.s3_bucket : aws_s3_bucket.staging[0].bucket
}

# If tfstate backend buckets/table are not present, you should create them outside or via another module.
# (This repo expects tfstate_bucket and tfstate_lock_table variables to be set.)

# IAM role for EC2 (SSM + s3 read to staging bucket)
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      identifiers = ["ec2.amazonaws.com"]
      type        = "Service"
    }
  }
}

resource "aws_iam_role" "ec2_ssm_role" {
  name               = "${var.name_prefix}-ec2-ssm-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ssm_managed" {
  role       = aws_iam_role.ec2_ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "s3_read_staging" {
  name = "${var.name_prefix}-s3-read-staging"
  role = aws_iam_role.ec2_ssm_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject"]
        Resource = "arn:aws:s3:::${local.staging_bucket}/*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.name_prefix}-instance-profile"
  role = aws_iam_role.ec2_ssm_role.name
}

# Key pair (optional)
resource "aws_key_pair" "deploy_key" {
  count      = length(trimspace(var.public_key)) > 0 ? 1 : 0
  key_name   = "${var.name_prefix}-key"
  public_key = var.public_key
}

# Security Group
resource "aws_security_group" "provision_sg" {
  name        = "${var.name_prefix}-sg"
  description = "Allow HTTP/HTTPS and SSH from allowed CIDRs"
  vpc_id      = var.vpc_id != "" ? var.vpc_id : null

  dynamic "ingress" {
    for_each = var.allowed_cidrs
    content {
      description = "SSH from list"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.name_prefix}-sg" }
}

# Use canonical Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

# user_data script (cloud-init) to ensure SSM agent is present
data "template_file" "user_data" {
  template = file("${path.module}/templates/install_ssm.sh")
  vars = { region = var.region }
}

resource "aws_instance" "provision" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = (length(aws_key_pair.deploy_key.*.key_name) > 0 ? aws_key_pair.deploy_key[0].key_name : null)
  vpc_security_group_ids = [aws_security_group.provision_sg.id]
  subnet_id              = var.subnet_id != "" ? var.subnet_id : null
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  user_data              = data.template_file.user_data.rendered
  associate_public_ip_address = var.associate_public_ip

  root_block_device {
    volume_size = var.root_volume_size
    volume_type = "gp3"
  }

  tags = {
    Name = "${var.name_prefix}-instance"
    Project = var.name_prefix
  }

  lifecycle {
    create_before_destroy = true
  }
}