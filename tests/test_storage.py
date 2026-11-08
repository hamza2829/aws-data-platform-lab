import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from data_platform_lab.storage import make_store


@pytest.mark.parametrize("endpoint", ["https://localhost:4566", "http://s3.amazonaws.com:4566",
                                      "http://localhost:443", "http://localhost:4566/path",
                                      "http://user:secret@localhost:4566", "http://localhost:4566?q=x",
                                      "http://localhost:4566#part"])
def test_reject_nonlocal_endpoints(endpoint):
    with pytest.raises(ValueError, match="LocalStack"):
        make_store(endpoint)


def test_optional_json_does_not_hide_permissions_errors(store):
    assert store.optional_json("missing") is None
    with Stubber(store.client) as stub:
        stub.add_client_error("get_object", service_error_code="AccessDenied", http_status_code=403)
        with pytest.raises(ClientError, match="AccessDenied"):
            store.optional_json("denied")


def test_local_client_and_assumed_role(monkeypatch, store):
    local = make_store()
    assert local.client.meta.endpoint_url == "http://localhost:4566"
    assert local.raw_bucket == "aws-data-platform-lab-raw"

    class FakeSTS:
        def assume_role(self, **kwargs):
            assert kwargs["RoleArn"] == "arn:aws:iam::000000000000:role/lab-pipeline"
            return dict(Credentials=dict(AccessKeyId="test", SecretAccessKey="test",
                                          SessionToken="test"))

    monkeypatch.setattr("data_platform_lab.storage.boto3.client",
                        lambda service, **kwargs: FakeSTS() if service == "sts" else store.client)
    result = make_store(role_arn="arn:aws:iam::000000000000:role/lab-pipeline")
    assert result.client is store.client
