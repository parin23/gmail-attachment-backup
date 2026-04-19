# Gmail Attachment Backup

Backup Gmail attachments to local storage or S3. Idempotent - same attachments are not processed twice.

## Features

- **Idempotent**: Uses SHA256 hash to track processed attachments
- **Multiple folders**: Backup INBOX, SENT, Starred, or any Gmail label
- **Configurable**: Fetch last X messages per folder run
- **Auto-numbering**: Duplicate filenames are auto-suffixed (`file.pdf` → `file_1.pdf`)
- **S3-compatible**: Works with AWS S3, MinIO, Backblaze B2, etc.
- **Docker**: Lightweight container (~164MB)

## Quick Start

### 1. Clone and Configure

```bash
cp config.yaml config.yaml
cp .env.example .env
```

Edit `config.yaml`:

```yaml
storage: local
local:
  root_dir: /app/backups

gmail:
  email: "your-email@gmail.com"
  app_password: "${GMAIL_APP_PASSWORD}"

backup:
  folders:
    - "INBOX"
    - "SENT"
    # - "Starred"
    # - "[Gmail]/Spam"
  message_limit: 100
```

Edit `.env`:

```bash
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### 2. Run with Docker

```bash
# Build
docker build -t gmail-backup .

# Run (DB is stored in backups/.backup_tracker.db)
docker run --rm \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/backups:/app/backups \
  --env-file .env \
  gmail-backup
```

Or use Docker Compose:

```bash
docker compose run gmail-backup
```

### 3. Schedule with Cron

```bash
# Run every 6 hours
0 */6 * * * docker compose run gmail-backup >> /path/to/backup.log 2>&1
```

## Configuration

### Storage Options

#### Local Storage

```yaml
storage: local
local:
  root_dir: /app/backups
```

Directory structure:
```
backups/
├── INBOX/
│   └── 2024/
│       └── 03/
│           └── 19/
│               └── abc123.../
│                   ├── document.pdf
│                   └── file_1.pdf
├── SENT/
│   └── ...
```

#### S3 Storage

```yaml
storage: s3
s3:
  endpoint: https://s3.amazonaws.com
  bucket: your-bucket-name
  access_key: ${S3_ACCESS_KEY}
  secret_key: ${S3_SECRET_KEY}
  region: us-east-1
```

S3 key format: `{folder}/{YYYY/MM/DD}/{hash}/{filename}`

### GMail Settings

- **App Password**: Enable 2FA on your Gmail account, then generate an App Password at https://myaccount.google.com/apppasswords
- **Folders**: Use Gmail labels (e.g., "INBOX", "SENT", "Starred"). For labels with slashes, use `[Gmail]/Spam` format

### Message Limit

`message_limit` controls how many recent messages to fetch per folder per run. Set based on how often you run the backup:
- Run daily → `message_limit: 50`
- Run every 6 hours → `message_limit: 100`

## Usage Without Docker

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Directly

```bash
python -m gmail_backup.backup
```

Or with environment variables:

```bash
GMAIL_APP_PASSWORD="xxxx" python -m gmail_backup.backup
```

## Troubleshooting

### Connection Failed

- Check app password is correct
- Ensure IMAP is enabled: Settings → Forwarding and POP/IMAP → Enable IMAP

### Permission Denied

```bash
chmod -R 777 backups backup_tracker.db
```

### View Logs

```bash
docker compose logs -f
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GMAIL_APP_PASSWORD` | Yes | Gmail App Password |
| `S3_ACCESS_KEY` | If S3 | S3 Access Key |
| `S3_SECRET_KEY` | If S3 | S3 Secret Key |

## Files

| File | Description |
|------|-------------|
| `backups/` | Local backup storage (including hidden `.backup_tracker.db`) |
| `.env` | Your credentials (never commit this) |

## Security Notes

- Never commit `.env` or credentials
- Use App Passwords, not your main password
- The tracker database uses SHA256 hashes - content is not encrypted