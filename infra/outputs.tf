output "raw_bucket" {
  value = aws_s3_bucket.layer["raw"].bucket
}

output "curated_bucket" {
  value = aws_s3_bucket.layer["curated"].bucket
}

output "pipeline_role_arn" {
  value = aws_iam_role.pipeline.arn
}

output "analyst_role_arn" {
  value = aws_iam_role.analyst.arn
}
