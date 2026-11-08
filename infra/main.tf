variable "prefix" {
  description = "Names for resources in the local emulator only"
  type        = string
  default     = "aws-data-platform-lab"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,40}$", var.prefix))
    error_message = "Use a short lower-case lab prefix."
  }
}

locals {
  layers = toset(["raw", "curated"])
}

resource "aws_s3_bucket" "layer" {
  for_each      = local.layers
  bucket        = "${var.prefix}-${each.key}"
  force_destroy = true
  tags = {
    Project     = "aws-data-platform-lab"
    Environment = "local-emulator"
    Layer       = each.key
  }
}

resource "aws_s3_bucket_versioning" "layer" {
  for_each = local.layers
  bucket   = aws_s3_bucket.layer[each.key].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "layer" {
  for_each   = local.layers
  bucket     = aws_s3_bucket.layer[each.key].id
  depends_on = [aws_s3_bucket_versioning.layer]
  rule {
    id     = "expire-obsolete-versions"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_public_access_block" "layer" {
  for_each                = local.layers
  bucket                  = aws_s3_bucket.layer[each.key].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "layer" {
  for_each = local.layers
  bucket   = aws_s3_bucket.layer[each.key].id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_iam_role" "pipeline" {
  name = "${var.prefix}-pipeline"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::000000000000:root" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "pipeline" {
  name = "pipeline-s3"
  role = aws_iam_role.pipeline.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:GetBucketLocation"]
        Resource = [for bucket in aws_s3_bucket.layer : bucket.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:GetObjectVersion"]
        Resource = [for bucket in aws_s3_bucket.layer : "${bucket.arn}/*"]
      }
    ]
  })
}

resource "aws_iam_role" "analyst" {
  name = "${var.prefix}-analyst"
  assume_role_policy = aws_iam_role.pipeline.assume_role_policy
}

resource "aws_iam_role_policy" "analyst" {
  name = "analyst-curated-read"
  role = aws_iam_role.analyst.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.layer["curated"].arn
        Condition = {
          StringLike = { "s3:prefix" = ["weather/*"] }
        }
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:GetObjectVersion"]
        Resource = "${aws_s3_bucket.layer["curated"].arn}/weather/*"
      }
    ]
  })
}
