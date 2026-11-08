from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from data_platform_lab.storage import S3Store

SOURCE = Path(__file__).resolve().parents[1] / "data/seattle-weather.csv"


@pytest.fixture
def source():
    return SOURCE


@pytest.fixture
def store():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1", aws_access_key_id="test",
                               aws_secret_access_key="test")
        for bucket in ("lab-raw", "lab-curated"):
            client.create_bucket(Bucket=bucket)
            client.put_bucket_versioning(Bucket=bucket,
                                          VersioningConfiguration={"Status": "Enabled"})
        yield S3Store(client, "lab-raw", "lab-curated")
