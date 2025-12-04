terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "qsr-dev"
}

# --- Networking (The Lean Version) ---

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "qsr-vpc" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "qsr-igw" }
}

data "aws_availability_zones" "available" {
  state = "available"
}

# --- Public Subnets (Where Airflow Lives) ---
resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = data.aws_availability_zones.available.names[0]
  tags                    = { Name = "qsr-public-subnet-1" }
}

resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  map_public_ip_on_launch = true
  availability_zone       = data.aws_availability_zones.available.names[1]
  tags                    = { Name = "qsr-public-subnet-2" }
}

# --- Route Table (Public) ---
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = { Name = "qsr-public-rt" }
}

resource "aws_route_table_association" "public_1" {
  subnet_id      = aws_subnet.public_1.id
  route_table_id = aws_route_table.public.id
}
resource "aws_route_table_association" "public_2" {
  subnet_id      = aws_subnet.public_2.id
  route_table_id = aws_route_table.public.id
}

# --- S3 Bucket (The Data Lake) ---
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "data_lake" {
  bucket        = "qsr-data-lake-${random_id.bucket_suffix.hex}"
  force_destroy = true
  tags          = { Name = "qsr-data-lake" }
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- IAM Role (Identity) ---
resource "aws_iam_role" "mwaa_role" {
  name = "qsr-mwaa-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = ["ec2.amazonaws.com"] }
    }]
  })
  tags = { Name = "qsr-mwaa-role" }
}

resource "aws_iam_role_policy" "mwaa_policy" {
  name = "qsr-mwaa-policy"
  role = aws_iam_role.mwaa_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject*", "s3:GetBucket*", "s3:List*", "s3:PutObject*", "s3:DeleteObject*"]
        Resource = [aws_s3_bucket.data_lake.arn, "${aws_s3_bucket.data_lake.arn}/*"]
      },
      {
        Effect = "Allow"
        Action = ["glue:*", "iam:PassRole"]
        Resource = "*"
      }
    ]
  })
}

# --- EC2 Security Group ---
resource "aws_security_group" "airflow_ec2_sg" {
  name        = "qsr-airflow-sg"
  description = "Allow SSH and Airflow Web UI"
  vpc_id      = aws_vpc.main.id

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Airflow Web UI
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "qsr-airflow-sg" }
}

# --- Key Pair ---
resource "tls_private_key" "pk" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "kp" {
  key_name   = "qsr-key"
  public_key = tls_private_key.pk.public_key_openssh
}

resource "local_file" "ssh_key" {
  filename = "qsr-key.pem"
  content  = tls_private_key.pk.private_key_pem
}

# --- IAM Instance Profile ---
resource "aws_iam_instance_profile" "airflow_profile" {
  name = "qsr-airflow-profile"
  role = aws_iam_role.mwaa_role.name
}

# --- EC2 Instance (Airflow Server) ---
resource "aws_instance" "airflow_server" {
  ami                    = "ami-04b4f1a9cf54c11d0" # Ubuntu 24.04 LTS us-east-1
  instance_type          = "t3.medium"
  subnet_id              = aws_subnet.public_1.id
  key_name               = aws_key_pair.kp.key_name
  vpc_security_group_ids = [aws_security_group.airflow_ec2_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.airflow_profile.name

  tags = { Name = "qsr-airflow-server" }
}

output "ssh_command" {
  value = "ssh -i qsr-key.pem ubuntu@${aws_instance.airflow_server.public_ip}"
}

output "airflow_url" {
  value = "http://${aws_instance.airflow_server.public_ip}:8080"
}

# --- Glue IAM Role (Identity for the Job) ---
resource "aws_iam_role" "glue_role" {
  name = "qsr-glue-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
    }]
  })
}

# Attach permission to Read/Write S3 and Logging
resource "aws_iam_role_policy" "glue_policy" {
  name = "qsr-glue-policy"
  role = aws_iam_role.glue_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_lake.arn,
          "${aws_s3_bucket.data_lake.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:/aws-glue/*"
      }
    ]
  })
}

# --- Upload Script to S3 ---
resource "aws_s3_object" "etl_script" {
  bucket = aws_s3_bucket.data_lake.id
  key    = "scripts/etl_script.py"
  source = "../scripts/etl_script.py" # Local file path
  etag   = filemd5("../scripts/etl_script.py")
}

# --- AWS Glue Job ---
resource "aws_glue_job" "clean_orders" {
  name     = "qsr-clean-orders-job"
  role_arn = aws_iam_role.glue_role.arn

  command {
    script_location = "s3://${aws_s3_bucket.data_lake.id}/scripts/etl_script.py"
    python_version  = "3"
  }

  default_arguments = {
    "--bucket_name" = aws_s3_bucket.data_lake.id
  }

  glue_version = "4.0"
  worker_type  = "G.1X" # Smallest worker type
  number_of_workers = 2
}





# --- Streaming Layer (Renting this: Comment out when done) ---

# 1. The Pipe (Kinesis Data Stream)
resource "aws_kinesis_stream" "order_stream" {
  name             = "qsr-real-time-orders"
  shard_count      = 1
  retention_period = 24
  tags             = { Name = "qsr-kinesis-stream" }
}

# 2. IAM Role for Firehose
resource "aws_iam_role" "firehose_role" {
  name = "qsr-firehose-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "firehose.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "firehose_policy" {
  name = "qsr-firehose-policy"
  role = aws_iam_role.firehose_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:AbortMultipartUpload",
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:ListBucketMultipartUploads",
          "s3:PutObject"
        ]
        Resource = [
          aws_s3_bucket.data_lake.arn,
          "${aws_s3_bucket.data_lake.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kinesis:DescribeStream",
          "kinesis:GetShardIterator",
          "kinesis:GetRecords",
          "kinesis:ListShards"
        ]
        Resource = aws_kinesis_stream.order_stream.arn
      }
    ]
  })
}

# 3. The Delivery Truck (Firehose -> S3)
resource "aws_kinesis_firehose_delivery_stream" "s3_stream" {
  name        = "qsr-firehose-to-s3"
  destination = "extended_s3"

  kinesis_source_configuration {
    kinesis_stream_arn = aws_kinesis_stream.order_stream.arn
    role_arn           = aws_iam_role.firehose_role.arn
  }

  extended_s3_configuration {
    role_arn   = aws_iam_role.firehose_role.arn
    bucket_arn = aws_s3_bucket.data_lake.arn
    
    # This separates Stream data from Batch data
    prefix              = "raw_stream/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/"
    error_output_prefix = "firehose_errors/"
    
    # Buffer: Write every 1MB or 60 seconds (Whichever comes first)
    buffering_size = 1
    buffering_interval = 60
  }
}

# --- Analytics Layer (Glue Crawler & Catalog) ---

# 1. The Database (A folder for your tables)
resource "aws_glue_catalog_database" "qsr_db" {
  name = "qsr_analytics_db"
}

# 2. IAM Role for Crawler (Permission to run)
resource "aws_iam_role" "crawler_role" {
  name = "qsr-crawler-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
    }]
  })
}

# Attach standard AWS managed policy for Glue services
resource "aws_iam_role_policy_attachment" "crawler_managed" {
  role       = aws_iam_role.crawler_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Attach specific S3 Access to OUR bucket
resource "aws_iam_role_policy" "crawler_s3" {
  name = "qsr-crawler-s3"
  role = aws_iam_role.crawler_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject"]
        Resource = [
          aws_s3_bucket.data_lake.arn,
          "${aws_s3_bucket.data_lake.arn}/*"
        ]
      }
    ]
  })
}

# 3. The Crawler (The Robot)
resource "aws_glue_crawler" "qsr_crawler" {
  database_name = aws_glue_catalog_database.qsr_db.name
  name          = "qsr-clean-data-crawler"
  role          = aws_iam_role.crawler_role.arn

  # Point it to the CLEAN folder (The Silver Layer)
  s3_target {
    path = "s3://${aws_s3_bucket.data_lake.id}/clean/"
  }
}