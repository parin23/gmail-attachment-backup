import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class GmailConfig:
    email: str
    app_password: str


@dataclass
class S3Config:
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str
    region: str = "us-east-1"


@dataclass
class LocalConfig:
    root_dir: Path


@dataclass
class BackupConfig:
    folders: list[str]
    message_limit: int = 100


@dataclass
class Config:
    storage: str = "s3"
    gmail: GmailConfig | None = None
    s3: S3Config | None = None
    local: LocalConfig | None = None
    backup: BackupConfig | None = None

    def get_gmail(self) -> GmailConfig:
        if self.gmail is None:
            raise ValueError("Gmail config not set")
        return self.gmail

    def get_backup(self) -> BackupConfig:
        if self.backup is None:
            raise ValueError("Backup config not set")
        return self.backup

    def get_s3(self) -> S3Config | None:
        return self.s3

    def get_local(self) -> LocalConfig | None:
        return self.local


def load_config(config_path: str | Path | None = None) -> Config:
    if config_path is None:
        config_path = Path.cwd() / "config.yaml"

    with open(config_path) as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    _resolve_env_vars(raw)

    storage = raw.get("storage", "s3")

    s3_config = None
    local_config = None

    if storage == "s3":
        s3_data = raw.get("s3", {})
        s3_config = S3Config(
            endpoint=s3_data.get("endpoint", ""),
            bucket=s3_data.get("bucket", ""),
            access_key=s3_data.get("access_key", ""),
            secret_key=s3_data.get("secret_key", ""),
            region=s3_data.get("region", "us-east-1"),
        )
    elif storage == "local":
        local_data = raw.get("local", {})
        local_config = LocalConfig(root_dir=Path(local_data.get("root_dir", "./backups")))

    return Config(
        storage=storage,
        gmail=GmailConfig(
            email=raw["gmail"]["email"],
            app_password=raw["gmail"]["app_password"],
        ),
        s3=s3_config,
        local=local_config,
        backup=BackupConfig(
            folders=raw["backup"]["folders"],
            message_limit=raw["backup"].get("message_limit", 100),
        ),
    )


def _resolve_env_vars(obj: Any) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                obj[key] = os.environ.get(env_var, "")
            elif isinstance(value, dict):
                _resolve_env_vars(value)
    elif isinstance(obj, list):
        for item in obj:
            _resolve_env_vars(item)