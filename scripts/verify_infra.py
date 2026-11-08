"""Check the applied Terraform resources with boto3 against LocalStack only."""

import json
from pathlib import Path

import boto3

endpoint = "http://localhost:4566"
credentials = dict(endpoint_url=endpoint, region_name="us-east-1",
                    aws_access_key_id="test", aws_secret_access_key="test")
s3, iam = boto3.client("s3", **credentials), boto3.client("iam", **credentials)
outputs = json.loads(Path("artifacts/terraform-outputs.json").read_text())
checks = []
for layer in ("raw", "curated"):
    bucket = outputs[f"{layer}_bucket"]["value"]
    s3.head_bucket(Bucket=bucket)
    assert s3.get_bucket_versioning(Bucket=bucket)["Status"] == "Enabled"
    lifecycle = s3.get_bucket_lifecycle_configuration(Bucket=bucket)["Rules"][0]
    assert lifecycle["Status"] == "Enabled"
    assert lifecycle["NoncurrentVersionExpiration"]["NoncurrentDays"] == 30
    assert lifecycle["AbortIncompleteMultipartUpload"]["DaysAfterInitiation"] == 7
    block = s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
    assert all(block.values())
    encryption = s3.get_bucket_encryption(Bucket=bucket)["ServerSideEncryptionConfiguration"]
    assert encryption["Rules"][0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256"
    checks.append(dict(layer=layer, bucket=bucket, versioning="Enabled", lifecycle=lifecycle,
                       public_access_block=block, encryption=encryption))
policies = {}
for kind, policy_name in (("pipeline", "pipeline-s3"), ("analyst", "analyst-curated-read")):
    role = outputs[f"{kind}_role_arn"]["value"].split("/")[-1]
    iam.get_role(RoleName=role)
    policy = iam.get_role_policy(RoleName=role, PolicyName=policy_name)["PolicyDocument"]
    statements = policy["Statement"]
    actions = {action for statement in statements for action in statement["Action"]}
    assert "s3:GetObject" in actions and "s3:ListBucket" in actions
    assert all(statement["Effect"] == "Allow" for statement in statements)
    if kind == "analyst":
        assert not any(action in actions for action in ("s3:PutObject", "s3:DeleteObject", "s3:*"))
        assert all("-raw" not in json.dumps(statement["Resource"]) for statement in statements)
        assert "weather/*" in statements[0]["Condition"]["StringLike"]["s3:prefix"]
    else:
        assert "s3:PutObject" in actions
    policies[kind] = policy
Path("artifacts/infra-verification.json").write_text(json.dumps(
    dict(endpoint=endpoint, buckets=checks, policies=policies, passed=True), indent=2) + "\n")
print("Verified both buckets, versioning, lifecycle, encryption, public access blocks, and IAM")
