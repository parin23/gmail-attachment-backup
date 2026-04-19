import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Generator


@dataclass
class ProcessedAttachment:
    id: int
    attachment_hash: str
    filename: str
    message_id: str
    s3_key: str
    processed_at: datetime


class IdempotencyTracker:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path.touch()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attachment_hash TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    s3_key TEXT NOT NULL,
                    folder TEXT NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_attachment_hash
                ON processed_attachments(attachment_hash)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_message_id
                ON processed_attachments(message_id)
            """)

    def is_processed(self, attachment_hash: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM processed_attachments WHERE attachment_hash = ?",
                (attachment_hash,),
            )
            return cursor.fetchone() is not None

    def mark_processed(
        self,
        attachment_hash: str,
        filename: str,
        message_id: str,
        s3_key: str,
        folder: str,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_attachments
                (attachment_hash, filename, message_id, s3_key, folder)
                VALUES (?, ?, ?, ?, ?)
                """,
                (attachment_hash, filename, message_id, s3_key, folder),
            )

    def get_all_processed(self) -> Generator[ProcessedAttachment, None, None]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM processed_attachments")
            for row in cursor:
                yield ProcessedAttachment(
                    id=row[0],
                    attachment_hash=row[1],
                    filename=row[2],
                    message_id=row[3],
                    s3_key=row[4],
                    processed_at=datetime.fromisoformat(row[6]),
                )

    def get_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*), COUNT(DISTINCT folder) FROM processed_attachments")
            row = cursor.fetchone()
            return {"total": row[0], "folders": row[1]}