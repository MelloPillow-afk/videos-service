"""The privileged guard is one unconditional PUT, including previously absent keys."""

import boto3
import pytest
from botocore.stub import Stubber
from mypy_boto3_s3 import S3Client

from src.config import Settings
from src.providers.r2 import R2Storage
from src.providers.storage import GUARD_CONTENT_TYPE, GUARD_METADATA_KEY, StorageArea


@pytest.mark.parametrize("area,bucket", [("private", "sources"), ("public", "delivery")])
async def test_seal_overwrites_atomically_and_head_verifies_marker(
    area: StorageArea, bucket: str
) -> None:
    client: S3Client = boto3.client(  # pyright: ignore[reportUnknownMemberType]
        "s3",
        region_name="auto",
        aws_access_key_id="controlled",
        aws_secret_access_key="controlled",
    )
    adapter = R2Storage(
        Settings(r2_private_bucket="sources", r2_public_bucket="delivery"), client=client
    )
    with Stubber(client) as stub:
        # Neither HEAD nor DELETE nor conditional create is allowed before this PUT.
        stub.add_response(
            "put_object",
            {},
            {
                "Bucket": bucket,
                "Key": "videos/example/reserved",
                "Body": b"",
                "ContentType": GUARD_CONTENT_TYPE,
                "Metadata": {GUARD_METADATA_KEY: "1"},
                "CacheControl": "no-store",
            },
        )
        stub.add_response(
            "head_object",
            {
                "ContentLength": 0,
                "ContentType": GUARD_CONTENT_TYPE,
                "Metadata": {GUARD_METADATA_KEY: "1"},
            },
            {"Bucket": bucket, "Key": "videos/example/reserved"},
        )
        await adapter.seal(area, "videos/example/reserved")
        observed = await adapter.head(area, "videos/example/reserved")
        assert observed is not None and observed.size_bytes == 0 and observed.deletion_guard
        assert observed.content_type == GUARD_CONTENT_TYPE
        stub.assert_no_pending_responses()


async def test_ordinary_r2_writer_cannot_request_privileged_overwrite() -> None:
    with pytest.raises(ValueError, match="create-only"):
        await R2Storage(Settings()).write(
            "public", "key", b"media", "video/mp2t", create_only=False
        )
