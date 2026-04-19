import logging
from datetime import datetime
from io import BytesIO
from typing import Generator

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class S3Client:
    def __init__(
        self,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=BotoConfig(signature_version="s3v4"),
        )

    def upload(
        self,
        data: bytes,
        key: str,
        content_type: str | None = None,
    ) -> str:
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        self._client.upload_fileobj(
            BytesIO(data),
            self.bucket,
            key,
            ExtraArgs=extra_args,
        )
        logger.info("Uploaded: %s", key)
        return key

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def download(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def list_objects(self, prefix: str = "") -> list[str]:
        results = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            if "Contents" not in page:
                continue
            for obj in page["Contents"]:
                results.append(obj["Key"])
        return results

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)
        logger.info("Deleted: %s", key)

    def get_url(self, key: str) -> str:
        return f"{self._client._endpoint.url}/{self.bucket}/{key}"


def build_s3_key(
    folder: str,
    attachment_hash: str,
    filename: str,
    message_date: datetime,
) -> str:
    date_prefix = message_date.strftime("%Y/%m/%d")
    safe_folder = folder.replace("/", "_")
    return f"{safe_folder}/{date_prefix}/{attachment_hash}/{filename}"