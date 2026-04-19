# Gmail Attachment Backup

Backup Gmail attachments to local storage or S3. Idempotent - same attachments are not processed twice.

## Features

- SHA256 hash tracking - no duplicates
- Multiple folders (INBOX, SENT, Starred, etc.)
- Auto-suffix duplicate filenames
- S3-compatible (AWS S3, MinIO, B2)

## Quick Start

```bash
# Install
pip install -e .

# Configure
cp config.yaml config.yaml
cp .env.example .env
```

Edit `config.yaml`:
```yaml
storage: local
local:
  root_dir: ./backups
gmail:
  email: "your-email@gmail.com"
  app_password: "${GMAIL_APP_PASSWORD}"
backup:
  folders: ["INBOX", "SENT"]
  message_limit: 100
```

Edit `.env`:
```bash
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

Run:
```bash
gmail-backup
```

## Schedule

### Cron (Linux/macOS)

```bash
# Run every 6 hours
0 */6 * * * gmail-backup >> /path/to/backup.log 2>&1
```

Or with Docker:
```bash
0 */6 * * * docker run --rm -v /path/to/config.yaml:/app/config.yaml:ro \
  -v /path/to/backups:/app/backups --env-file /path/to/.env \
  gmail-backup >> /path/to/backup.log 2>&1
```

### Task Scheduler (Windows)

```powershell
# CLI (recommended)
$action = New-ScheduledTaskAction -Execute 'gmail-backup'
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
Register-ScheduledTask -TaskName "GmailBackup" -Action $action -Trigger $trigger -Force
```

### Systemd (Linux)

`/etc/systemd/system/gmail-backup.service`:
```ini
[Service]
Type=oneshot
ExecStart=/usr/bin/docker run --rm -v /path/to/config.yaml:/app/config.yaml:ro \
  -v /path/to/backups:/app/backups --env-file /path/to/.env gmail-backup
```

`/etc/systemd/system/gmail-backup.timer`:
```ini
[Timer]
OnCalendar=*:0/6

[Install]
WantedBy=timers.target
```
```bash
sudo systemctl enable gmail-backup.timer
sudo systemctl start gmail-backup.timer
```

## Docker

```bash
# Build
docker build -t gmail-backup .

# Run
docker run --rm \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/backups:/app/backups \
  --env-file .env \
  gmail-backup
```

Or from Docker Hub:
```bash
docker run --rm -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/backups:/app/backups \
  -e GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx" \
  parin23/gmail-attachment-backup
```

## Configuration

| Option | Description |
|--------|-------------|
| `storage` | `local` or `s3` |
| `folders` | Gmail labels to backup |
| `message_limit` | Messages per folder per run |

### S3 Example

```yaml
storage: s3
s3:
  endpoint: https://s3.amazonaws.com
  bucket: your-bucket
  access_key: ${S3_ACCESS_KEY}
  secret_key: ${S3_SECRET_KEY}
  region: us-east-1
```

### App Password

Enable 2FA on your Gmail account, then generate an App Password at https://myaccount.google.com/apppasswords

## Troubleshooting

**Connection failed**: Check IMAP is enabled in Gmail settings

**Permission denied**: Run with appropriate permissions or `chmod -R 777 backups/`

**First run**: Database `backups/.backup_tracker.db` is created automatically