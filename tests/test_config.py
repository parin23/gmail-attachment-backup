import os
import tempfile
from pathlib import Path

import pytest
import yaml

from gmail_backup.config import (
    BackupConfig,
    Config,
    GmailConfig,
    S3Config,
    load_config,
)


@pytest.fixture
def config_file():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        data = {
            "gmail": {
                "email": "test@gmail.com",
                "app_password": "${TEST_APP_PASSWORD}",
            },
            "s3": {
                "endpoint": "https://s3.example.com",
                "bucket": "test-bucket",
                "access_key": "test-key",
                "secret_key": "test-secret",
                "region": "us-east-1",
            },
            "backup": {
                "folders": ["INBOX", "SENT"],
                "message_limit": 50,
            },
        }
        yaml.dump(data, f)
        path = f.name

    yield Path(path)

    Path(path).unlink(missing_ok=True)


def test_load_config_basic(config_file, monkeypatch):
    monkeypatch.setenv("TEST_APP_PASSWORD", "mysecret")

    config = load_config(config_file)

    assert config.gmail.email == "test@gmail.com"
    assert config.gmail.app_password == "mysecret"
    assert config.s3.bucket == "test-bucket"
    assert config.backup.folders == ["INBOX", "SENT"]
    assert config.backup.message_limit == 50


def test_load_config_defaults(config_file, monkeypatch):
    monkeypatch.setenv("TEST_APP_PASSWORD", "secret")

    data = {
        "gmail": {
            "email": "test@gmail.com",
            "app_password": "secret",
        },
        "s3": {
            "endpoint": "https://s3.example.com",
            "bucket": "test-bucket",
            "access_key": "key",
            "secret_key": "secret",
        },
        "backup": {
            "folders": ["INBOX"],
        },
    }

    with open(config_file, "w") as f:
        yaml.dump(data, f)

    config = load_config(config_file)

    assert config.s3.region == "us-east-1"
    assert config.backup.message_limit == 100


def test_gmail_config_dataclass():
    config = GmailConfig(
        email="user@gmail.com",
        app_password="password123",
    )

    assert config.email == "user@gmail.com"
    assert config.app_password == "password123"


def test_s3_config_dataclass():
    config = S3Config(
        endpoint="https://s3.example.com",
        bucket="bucket",
        access_key="key",
        secret_key="secret",
        region="eu-west-1",
    )

    assert config.endpoint == "https://s3.example.com"
    assert config.region == "eu-west-1"


def test_backup_config_dataclass():
    config = BackupConfig(
        folders=["INBOX", "Sent", "[Gmail]/Spam"],
        message_limit=200,
    )

    assert config.folders == ["INBOX", "Sent", "[Gmail]/Spam"]
    assert config.message_limit == 200


def test_config_dataclass():
    gmail = GmailConfig("a@b.com", "pass")
    s3 = S3Config(
        "https://s3.example.com", "bucket", "key", "secret"
    )
    backup = BackupConfig(["INBOX"], 100)

    config = Config(gmail=gmail, s3=s3, backup=backup)

    assert config.gmail.email == "a@b.com"
    assert config.s3.bucket == "bucket"
    assert config.backup.message_limit == 100