terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# --- VPC & Networking ---
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "text2sql-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
}

# --- Security Groups ---
resource "aws_security_group" "db_sg" {
  name        = "text2sql-db-sg"
  description = "Allow AppRunner to access RDS"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- RDS Database (MySQL) ---
resource "aws_db_subnet_group" "main" {
  name       = "text2sql-db-subnet-group"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_db_instance" "mysql" {
  identifier           = "text2sql-db"
  allocated_storage    = 20
  storage_type         = "gp2"
  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = "db.t3.micro"
  db_name              = var.db_name
  username             = var.db_username
  password             = var.db_password
  parameter_group_name = "default.mysql8.0"
  skip_final_snapshot  = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db_sg.id]
}

# --- App Runner IAM Role ---
resource "aws_iam_role" "apprunner_instance_role" {
  name = "text2sql-apprunner-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

# Policy to allow Bedrock access
resource "aws_iam_role_policy" "bedrock_policy" {
  name = "text2sql-bedrock-policy"
  role = aws_iam_role.apprunner_instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = ["arn:aws:bedrock:${var.aws_region}::foundation-model/*"]
      }
    ]
  })
}

# --- App Runner Service ---
resource "aws_apprunner_service" "backend" {
  service_name = "text2sql-backend"

  source_configuration {
    # For a real deployment, we'd use an ECR image or a GitHub source connection.
    # Placeholder using image repository
    image_repository {
      image_configuration {
        port = "8000"
        runtime_environment_variables = {
          DB_HOST = aws_db_instance.mysql.address
          DB_NAME = aws_db_instance.mysql.db_name
          DB_USER = var.db_username
          DB_PASS = var.db_password
        }
      }
      image_identifier      = "public.ecr.aws/aws-containers/hello-app-runner:latest" # Placeholder
      image_repository_type = "ECR_PUBLIC"
    }
  }

  instance_configuration {
    instance_role_arn = aws_iam_role.apprunner_instance_role.arn
  }

  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.connector.arn
    }
  }
}

resource "aws_apprunner_vpc_connector" "connector" {
  vpc_connector_name = "text2sql-vpc-connector"
  subnets            = module.vpc.private_subnets
  security_groups    = [aws_security_group.db_sg.id]
}
