FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY gmail_backup/ ./gmail_backup/

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "gmail_backup.backup"]