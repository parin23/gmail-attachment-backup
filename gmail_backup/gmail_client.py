import email
import hashlib
import imaplib
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.parser import BytesParser
from typing import Generator

logger = logging.getLogger(__name__)


@dataclass
class Attachment:
    filename: str
    content_type: str
    data: bytes
    message_id: str
    message_date: datetime


@dataclass
class Email:
    message_id: str
    subject: str
    sender: str
    date: datetime
    attachments: list[Attachment]


class GmailClient:
    def __init__(self, email: str, app_password: str):
        self.email = email
        self.app_password = app_password
        self._conn: imaplib.IMAP4_SSL | None = None

    def connect(self) -> None:
        self._conn = imaplib.IMAP4_SSL("imap.gmail.com")
        self._conn.login(self.email, self.app_password)
        logger.info("Connected to Gmail IMAP as %s", self.email)

    def disconnect(self) -> None:
        if self._conn:
            self._conn.logout()
            self._conn = None

    def fetch_messages(
        self, folder: str, limit: int
    ) -> Generator[Email, None, None]:
        if not self._conn:
            raise RuntimeError("Not connected. Call connect() first.")

        status, _ = self._conn.select(folder)
        if status != "OK":
            logger.warning("Failed to select folder: %s", folder)
            return

        status, message_ids = self._conn.search(None, "ALL")
        if status != "OK":
            return

        all_ids = message_ids[0].split()
        recent_ids = all_ids[-limit:]

        for msg_id in reversed(recent_ids):
            email = self._fetch_single(msg_id.decode(), folder)
            if email and email.attachments:
                yield email

    def _fetch_single(self, msg_id: str, folder: str) -> Email | None:
        assert self._conn

        status, msg_data = self._conn.fetch(msg_id, "(RFC822)")
        if status != "OK":
            return None

        raw_email = msg_data[0][1]
        parser = BytesParser(policy=policy.default)
        message = parser.parsebytes(raw_email)

        msg_id_header = message.get("Message-ID", "")
        subject = message.get("Subject", "(No Subject)")
        sender = message.get("From", "Unknown")
        date_str = message.get("Date", "")

        date = self._parse_date(date_str)

        attachments = self._extract_attachments(message, msg_id_header)

        return Email(
            message_id=msg_id_header,
            subject=subject,
            sender=sender,
            date=date,
            attachments=attachments,
        )

    def _extract_attachments(
        self, message: "email.message.Message", msg_id: str
    ) -> list[Attachment]:
        attachments = []

        for part in message.walk():
            if part.get_content_disposition() != "attachment":
                continue

            filename = part.get_filename()
            if not filename:
                continue

            filename = self._decode_filename(filename)
            content_type = part.get_content_type()
            data = part.get_payload(decode=True)

            if data:
                attachments.append(
                    Attachment(
                        filename=filename,
                        content_type=content_type,
                        data=data,
                        message_id=msg_id,
                        message_date=datetime.now(),
                    )
                )

        return attachments

    def _decode_filename(self, filename: str) -> str:
        match = re.match(r"=\?([^?]+)\?=", filename)
        if match:
            return filename.split("?")[-1] or filename
        return filename

    def _parse_date(self, date_str: str) -> datetime:
        try:
            return email.utils.parsedate_to_datetime(date_str)
        except Exception:
            return datetime.now()


def compute_attachment_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()