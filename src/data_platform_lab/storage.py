"""S3 transport; command-line clients are restricted to emulator endpoints."""

import json
from dataclasses import dataclass
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


@dataclass
class S3Store:
    client: object
    raw_bucket: str
    curated_bucket: str

    def put(self, bucket: str, key: str, payload: bytes, content_type: str = "application/json"):
        return self.client.put_object(Bucket=bucket, Key=key, Body=payload,
                                      ContentType=content_type, ServerSideEncryption="AES256")

    def read(self, bucket: str, key: str) -> tuple[bytes, str | None]:
        result = self.client.get_object(Bucket=bucket, Key=key)
        return result["Body"].read(), result.get("VersionId")

    def optional_json(self, key: str) -> dict | None:
        try:
            payload, _ = self.read(self.curated_bucket, key)
        except ClientError as exc:
            if exc.response["Error"]["Code"] in {"NoSuchKey", "404"}:
                return None
            raise
        return json.loads(payload)

    def keys(self, bucket: str, prefix: str) -> list[str]:
        pages = self.client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix)
        return sorted(item["Key"] for page in pages for item in page.get("Contents", []))

    def history(self) -> list[dict]:
        return [self.optional_json(key) for key in self.keys(self.curated_bucket, "_history/")]


def make_store(endpoint: str = "http://localhost:4566", prefix: str = "aws-data-platform-lab",
               role_arn: str | None = None) -> S3Store:
    parsed = urlparse(endpoint)
    if (parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "localstack"}
            or parsed.port != 4566 or parsed.path not in {"", "/"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("only local LocalStack HTTP endpoints on port 4566 are allowed")
    credentials = dict(aws_access_key_id="test", aws_secret_access_key="test")
    if role_arn:
        sts = boto3.client("sts", endpoint_url=endpoint, region_name="us-east-1", **credentials)
        result = sts.assume_role(RoleArn=role_arn, RoleSessionName="data-platform-lab")["Credentials"]
        credentials = dict(aws_access_key_id=result["AccessKeyId"],
                           aws_secret_access_key=result["SecretAccessKey"],
                           aws_session_token=result["SessionToken"])
    client = boto3.client("s3", endpoint_url=endpoint, region_name="us-east-1",
                          config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 3}),
                          **credentials)
    return S3Store(client, f"{prefix}-raw", f"{prefix}-curated")
