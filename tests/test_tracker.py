import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from gmail_backup.tracker import IdempotencyTracker, ProcessedAttachment


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield Path(path)
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def tracker(db_path):
    return IdempotencyTracker(db_path)


def test_init_creates_tables(tracker, db_path):
    assert db_path.exists()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor]

    assert "processed_attachments" in tables


def test_is_processed_false_when_empty(tracker):
    result = tracker.is_processed("abc123")
    assert result is False


def test_mark_processed_and_is_processed(tracker):
    tracker.mark_processed(
        attachment_hash="hash123",
        filename="test.pdf",
        message_id="<msg123@example.com>",
        s3_key="inbox/2024/01/01/hash123/test.pdf",
        folder="INBOX",
    )

    assert tracker.is_processed("hash123") is True


def test_is_processed_false_for_different_hash(tracker):
    tracker.mark_processed(
        attachment_hash="hash1",
        filename="test.pdf",
        message_id="<msg@example.com>",
        s3_key="inbox/hash1/test.pdf",
        folder="INBOX",
    )

    assert tracker.is_processed("hash2") is False


def test_mark_processed_ignores_duplicates(tracker):
    tracker.mark_processed(
        attachment_hash="hash123",
        filename="test.pdf",
        message_id="<msg1@example.com>",
        s3_key="inbox/test.pdf",
        folder="INBOX",
    )

    tracker.mark_processed(
        attachment_hash="hash123",
        filename="test2.pdf",
        message_id="<msg2@example.com>",
        s3_key="inbox/test2.pdf",
        folder="SENT",
    )

    assert tracker.is_processed("hash123") is True


def test_get_stats(tracker):
    tracker.mark_processed(
        attachment_hash="hash1",
        filename="a.pdf",
        message_id="<msg1@example.com>",
        s3_key="inbox/a.pdf",
        folder="INBOX",
    )

    tracker.mark_processed(
        attachment_hash="hash2",
        filename="b.pdf",
        message_id="<msg2@example.com>",
        s3_key="sent/b.pdf",
        folder="SENT",
    )

    stats = tracker.get_stats()
    assert stats["total"] == 2
    assert stats["folders"] == 2