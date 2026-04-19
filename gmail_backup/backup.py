import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from gmail_backup.config import Config, load_config
from gmail_backup.gmail_client import GmailClient, compute_attachment_hash
from gmail_backup.local_client import LocalStorageClient, build_local_key
from gmail_backup.s3_client import S3Client, build_s3_key
from gmail_backup.tracker import IdempotencyTracker

logger = logging.getLogger(__name__)


class StorageClient(Protocol):
    def upload(self, data: bytes, key: str, content_type: str | None = None) -> str: ...
    def exists(self, key: str) -> bool: ...
    def download(self, key: str) -> bytes: ...
    def list_objects(self, prefix: str = "") -> list[str]: ...
    def get_url(self, key: str) -> str: ...


@dataclass
class BackupResult:
    folder: str
    processed: int
    skipped: int
    errors: int


class BackupOrchestrator:
    def __init__(self, config: Config, db_path: str | Path | None = None):
        self.config = config
        self.db_path = db_path or Path.cwd() / "backup_tracker.db"
        self.storage = self._create_storage()

        self.gmail = GmailClient(config.get_gmail().email, config.get_gmail().app_password)
        self.tracker = IdempotencyTracker(self.db_path)

    def _create_storage(self) -> StorageClient:
        if self.config.storage == "local":
            if not self.config.local:
                raise ValueError("Local storage configured but local.root_dir not set")
            return LocalStorageClient(self.config.local.root_dir)
        else:
            if not self.config.s3:
                raise ValueError("S3 storage configured but s3 config not set")
            return S3Client(
                self.config.s3.endpoint,
                self.config.s3.bucket,
                self.config.s3.access_key,
                self.config.s3.secret_key,
                self.config.s3.region,
            )

    def run(self) -> list[BackupResult]:
        results = []

        try:
            self.gmail.connect()

            for folder in self.config.get_backup().folders:
                result = self._backup_folder(folder)
                results.append(result)

        finally:
            self.gmail.disconnect()

        return results

    def _backup_folder(self, folder: str) -> BackupResult:
        processed = 0
        skipped = 0
        errors = 0

        logger.info("Processing folder: %s", folder)

        for email in self.gmail.fetch_messages(
            folder, self.config.get_backup().message_limit
        ):
            for attachment in email.attachments:
                attachment_hash = compute_attachment_hash(attachment.data)

                if self.tracker.is_processed(attachment_hash):
                    skipped += 1
                    continue

                try:
                    if self.config.storage == "local":
                        storage_path = build_local_key(
                            folder,
                            attachment_hash,
                            attachment.filename,
                            attachment.message_date,
                        )
                    else:
                        storage_path = build_s3_key(
                            folder,
                            attachment_hash,
                            attachment.filename,
                            attachment.message_date,
                        )

                    self.storage.upload(
                        attachment.data,
                        storage_path,
                        attachment.content_type,
                    )

                    self.tracker.mark_processed(
                        attachment_hash,
                        attachment.filename,
                        email.message_id,
                        storage_path,
                        folder,
                    )

                    processed += 1

                except Exception as e:
                    logger.error(
                        "Failed to upload %s: %s",
                        attachment.filename,
                        e,
                    )
                    errors += 1

        logger.info(
            "Folder %s: processed=%d, skipped=%d, errors=%d",
            folder,
            processed,
            skipped,
            errors,
        )

        return BackupResult(
            folder=folder,
            processed=processed,
            skipped=skipped,
            errors=errors,
        )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    try:
        config = load_config()
    except Exception as e:
        logger.error("Failed to load config: %s", e)
        return 1

    orchestrator = BackupOrchestrator(config)
    results = orchestrator.run()

    total_processed = sum(r.processed for r in results)
    total_skipped = sum(r.skipped for r in results)
    total_errors = sum(r.errors for r in results)

    logger.info(
        "Total: processed=%d, skipped=%d, errors=%d",
        total_processed,
        total_skipped,
        total_errors,
    )

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())