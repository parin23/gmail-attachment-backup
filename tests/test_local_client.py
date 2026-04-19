import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from gmail_backup.local_client import LocalStorageClient, build_local_key


class TestBuildLocalKey:
    def test_basic_key_construction(self):
        key = build_local_key(
            folder="INBOX",
            attachment_hash="abc123def456",
            filename="document.pdf",
            message_date=datetime(2024, 3, 15, 10, 30, 0),
        )

        assert key == "INBOX/2024/03/15/abc123def456/document.pdf"

    def test_folder_with_spaces(self):
        key = build_local_key(
            folder="Custom Label",
            attachment_hash="hash",
            filename="file.zip",
            message_date=datetime(2024, 1, 1),
        )

        assert key == "Custom Label/2024/01/01/hash/file.zip"


@pytest.fixture
def temp_root():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def storage_client(temp_root):
    return LocalStorageClient(temp_root)


class TestLocalStorageClient:
    def test_upload_creates_directories(self, storage_client, temp_root):
        storage_client.upload(
            b"test content",
            "folder/2024/01/01/hash/file.txt",
            None,
        )

        assert (temp_root / "folder" / "2024" / "01" / "01" / "hash" / "file.txt").exists()

    def test_upload_returns_relative_path(self, storage_client, temp_root):
        result = storage_client.upload(
            b"test",
            "inbox/2024/03/15/abc/file.txt",
            None,
        )

        assert result == "inbox/2024/03/15/abc/file.txt"

    def test_exists_true_when_file_exists(self, storage_client, temp_root):
        storage_client.upload(b"test", "folder/file.txt", None)

        result = storage_client.exists("folder/file.txt")

        assert result is True

    def test_exists_false_when_missing(self, storage_client, temp_root):
        result = storage_client.exists("folder/missing.txt")

        assert result is False

    def test_download_returns_content(self, storage_client, temp_root):
        storage_client.upload(b"hello world", "folder/file.txt", None)

        content = storage_client.download("folder/file.txt")

        assert content == b"hello world"

    def test_list_objects(self, storage_client, temp_root):
        storage_client.upload(b"a", "folder1/file1.txt", None)
        storage_client.upload(b"b", "folder1/file2.txt", None)
        storage_client.upload(b"c", "folder2/file3.txt", None)

        results = storage_client.list_objects("folder1/")

        assert set(results) == {"folder1/file1.txt", "folder1/file2.txt"}

    def test_get_url(self, storage_client, temp_root):
        url = storage_client.get_url("folder/file.txt")

        assert url == f"file://{temp_root}/folder/file.txt"


class TestAutoNumbering:
    def test_duplicate_filename_gets_suffix(self, storage_client, temp_root):
        storage_client.upload(b"original", "folder/file.pdf", None)
        result = storage_client.upload(b"duplicate", "folder/file.pdf", None)

        assert "folder/file_1.pdf" == result

    def test_multiple_duplicates_increment(self, storage_client, temp_root):
        storage_client.upload(b"v1", "folder/doc.txt", None)
        storage_client.upload(b"v2", "folder/doc.txt", None)
        result = storage_client.upload(b"v3", "folder/doc.txt", None)

        assert result == "folder/doc_2.txt"

    def test_different_extension_no_collision(self, storage_client, temp_root):
        storage_client.upload(b"pdf content", "folder/file.pdf", None)
        result = storage_client.upload(b"doc content", "folder/file.doc", None)

        assert result == "folder/file.doc"

    def test_no_duplicate_of_already_numbered(self, storage_client, temp_root):
        storage_client.upload(b"v1", "folder/file.txt", None)
        storage_client.upload(b"v2", "folder/file_1.txt", None)
        result = storage_client.upload(b"v3", "folder/file.txt", None)

        assert result == "folder/file_2.txt"