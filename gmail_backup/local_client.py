import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)


class LocalStorageClient:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)

    def upload(
        self,
        data: bytes,
        key: str,
        content_type: str | None = None,
    ) -> str:
        relative_path = self._build_path(key)
        full_path = self.root_dir / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        final_path = self._resolve_duplicate_filename(full_path)

        with open(final_path, "wb") as f:
            f.write(data)

        logger.info("Saved: %s", final_path)
        return str(final_path.relative_to(self.root_dir))

    def exists(self, key: str) -> bool:
        relative_path = self._build_path(key)
        full_path = self.root_dir / relative_path
        if full_path.exists():
            return True
        if not full_path.parent.exists():
            return False
        return any(
            p.exists() for p in full_path.parent.iterdir()
            if p.stem.startswith(full_path.stem)
        )

    def download(self, key: str) -> bytes:
        full_path = self.root_dir / key
        if full_path.is_file():
            with open(full_path, "rb") as f:
                return f.read()

        for f in full_path.parent.iterdir():
            if f.stem.startswith(full_path.stem):
                with open(f, "rb") as f:
                    return f.read()

        raise FileNotFoundError(f"No file found for key: {key}")

    def list_objects(self, prefix: str = "") -> list[str]:
        search_dir = self.root_dir / prefix if prefix else self.root_dir

        if not search_dir.exists():
            return []

        results = []
        for root, _, files in os.walk(search_dir):
            for filename in files:
                full_path = Path(root) / filename
                results.append(str(full_path.relative_to(self.root_dir)))
        return results

    def delete(self, key: str) -> None:
        full_path = self.root_dir / key
        if full_path.exists():
            full_path.unlink()
            logger.info("Deleted: %s", full_path)

    def get_url(self, key: str) -> str:
        return f"file://{self.root_dir / key}"

    def _build_path(self, key: str) -> Path:
        return self.root_dir / key

    def _resolve_duplicate_filename(self, path: Path) -> Path:
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        directory = path.parent
        counter = 1

        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = directory / new_name
            if not new_path.exists():
                return new_path
            counter += 1


def build_local_key(
    folder: str,
    attachment_hash: str,
    filename: str,
    message_date: datetime,
) -> str:
    date_prefix = message_date.strftime("%Y_%m")
    safe_folder = folder.replace("/", "_")
    name,ext = os.path.splitext(filename)
    return f"{safe_folder}/{date_prefix}/{name}.{attachment_hash[0:3]}.{ext}"
