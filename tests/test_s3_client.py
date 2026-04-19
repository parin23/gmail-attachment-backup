from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from gmail_backup.s3_client import S3Client, build_s3_key


class TestBuildS3Key:
    def test_basic_key_construction(self):
        key = build_s3_key(
            folder="INBOX",
            attachment_hash="abc123def456",
            filename="document.pdf",
            message_date=datetime(2024, 3, 15, 10, 30, 0),
        )

        assert key == "INBOX/2024/03/15/abc123def456/document.pdf"

    def test_folder_with_spaces_replaced(self):
        key = build_s3_key(
            folder="Custom Label",
            attachment_hash="hash",
            filename="file.zip",
            message_date=datetime(2024, 1, 1),
        )

        assert key == "Custom Label/2024/01/01/hash/file.zip"

    def test_folder_slash_replaced(self):
        key = build_s3_key(
            folder="[Gmail]/Sent Mail",
            attachment_hash="hash",
            filename="file.pdf",
            message_date=datetime(2024, 6, 20),
        )

        assert key == "[Gmail]_Sent Mail/2024/06/20/hash/file.pdf"


class TestS3Client:
    @pytest.fixture
    def mock_boto3_session(self):
        with patch("gmail_backup.s3_client.boto3") as mock:
            mock_client = MagicMock()
            mock.client.return_value = mock_client
            yield mock_client

    def test_upload_calls_boto3(self, mock_boto3_session):
        client = S3Client(
            endpoint="https://s3.example.com",
            bucket="test-bucket",
            access_key="test-key",
            secret_key="test-secret",
            region="us-west-2",
        )

        client.upload(b"test data", "path/to/file.txt", "text/plain")

        mock_boto3_session.upload_fileobj.assert_called_once()

    def test_exists_returns_true(self, mock_boto3_session):
        client = S3Client(
            endpoint="https://s3.example.com",
            bucket="test-bucket",
            access_key="key",
            secret_key="secret",
        )

        result = client.exists("existing.txt")

        mock_boto3_session.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="existing.txt"
        )
        assert result is True

    def test_exists_returns_false(self, mock_boto3_session):
        from botocore.exceptions import ClientError

        mock_boto3_session.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )

        client = S3Client(
            endpoint="https://s3.example.com",
            bucket="test-bucket",
            access_key="key",
            secret_key="secret",
        )

        result = client.exists("nonexistent.txt")

        assert result is False

    def test_list_objects(self, mock_boto3_session):
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "file1.txt"}, {"Key": "file2.txt"}]},
            {"Contents": [{"Key": "file3.txt"}]},
        ]
        mock_boto3_session.get_paginator.return_value = mock_paginator

        client = S3Client(
            endpoint="https://s3.example.com",
            bucket="test-bucket",
            access_key="key",
            secret_key="secret",
        )

        results = list(client.list_objects("prefix/"))

        assert results == ["file1.txt", "file2.txt", "file3.txt"]