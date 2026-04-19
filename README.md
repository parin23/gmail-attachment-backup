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

### 2. Build & Run

```bash
# Build the Docker image
docker build -t gmail-backup .

# Run with Docker Compose
docker compose up

# Or run directly
docker run --rm \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/backups:/app/backups \
  --env-file .env \
  gmail-backup
```

### 3. Schedule with Cron (Linux/macOS)

```bash
# Run every 6 hours
0 */6 * * * cd /path/to/gmail-attachment-backup && docker compose run gmail-backup >> /path/to/backup.log 2>&1

# Or use docker run directly
0 */6 * * * docker run --rm \
  -v /path/to/gmail-attachment-backup/config.yaml:/app/config.yaml:ro \
  -v /path/to/gmail-attachment-backup/backups:/app/backups \
  --env-file /path/to/gmail-attachment-backup/.env \
  gmail-backup >> /path/to/backup.log 2>&1
```

### 3. Schedule with Task Scheduler (Windows)

**Option A: Using batch file**

1. Create `run-backup.bat`:
```batch
@echo off
docker run --rm -v "%~dp0config.yaml:/app/config.yaml:ro" -v "%~dp0backups:/app/backups" --env-file "%~dp0.env" gmail-backup
```

2. Open Task Scheduler → Create Task → Configure:
   - **Trigger**: Daily at selected time, or every 6 hours
   - **Action**: Start a program
   - **Program**: `C:\path\to\run-backup.bat`
   - **Start in**: `C:\path\to\gmail-attachment-backup`

**Option B: Using docker directly in Task Scheduler**

1. Open Task Scheduler → Create Task
2. **General**:
   - Name: Gmail Backup
   - Run whether user is logged on or not
   - Run with highest privileges (if needed)
3. **Triggers**: Daily at selected time, or repeat every 6 hours
4. **Actions**: Start a program
   ```
   Program: docker
   Arguments: run --rm -v "%USERPROFILE%\path\to\config.yaml:/app/config.yaml:ro" -v "%USERPROFILE%\path\to\backups:/app/backups" --env-file "%USERPROFILE%\path\to\.env" gmail-backup
   ```
   (Adjust paths as needed)
5. **Conditions**: Start only if network available (optional)
6. **Settings**: Run task as soon as possible if missed

**Option C: Using Windows Terminal (Windows 10/11)**

```powershell
# Run as ScheduledTask with PowerShell
$action = New-ScheduledTaskAction -Execute 'docker' -Argument 'run --rm -v "C:\path\to\config.yaml:/app/config.yaml:ro" -v "C:\path\to\backups:/app/backups" --env-file "C:\path\to\.env" gmail-backup'
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
Register-ScheduledTask -TaskName "GmailBackup" -Action $action -Trigger $trigger -Force
```

### Schedule with systemd (Linux)

Create `/etc/systemd/system/gmail-backup.service`:
```ini
[Unit]
Description=Gmail Attachment Backup

[Service]
Type=oneshot
WorkingDirectory=/path/to/gmail-attachment-backup
ExecStart=/usr/bin/docker compose run gmail-backup
```

Create `/etc/systemd/system/gmail-backup.timer`:
```ini
[Unit]
Description=Run Gmail Backup every 6 hours

[Timer]
OnCalendar=*:0/6
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl enable gmail-backup.timer
sudo systemctl start gmail-backup.timer
```

## Docker Usage

### Build Image

```bash
docker build -t gmail-backup .
```

### Run from Built Image

```bash
docker run --rm \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/backups:/app/backups \
  --env-file .env \
  gmail-backup
```

### Run from Docker Hub (No Build Required)

```bash
docker run --rm \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/backups:/app/backups \
  -e GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx" \
  ghcr.io/yourusername/gmail-backup:latest
```

Note: Replace the image URL with your published image path.

### Docker Compose

```bash
# Build and run
docker compose up

# Run only (use existing build)
docker compose run gmail-backup

# View logs
docker compose logs -f

# Stop
docker compose down
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
├── .backup_tracker.db    # SQLite database (auto-created)
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
chmod -R 777 backups
```

### View Logs

```bash
docker compose logs -f
```

### First Run Creates Database

On first run, the database file `backups/.backup_tracker.db` is created automatically. Subsequent runs will use the existing database.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GMAIL_APP_PASSWORD` | Yes | Gmail App Password |
| `S3_ACCESS_KEY` | If S3 | S3 Access Key |
| `S3_SECRET_KEY` | If S3 | S3 Secret Key |

## Files

| File | Description |
|------|-------------|
| `backups/` | Local backup storage (including `.backup_tracker.db`) |
| `.env` | Your credentials (never commit this) |
| `config.yaml` | Configuration (edit before running) |

## Security Notes

- Never commit `.env` or credentials
- Use App Passwords, not your main password
- The tracker database uses SHA256 hashes - content is not encrypted