# 📝 Referat - Active Session Memory & Context

This file is automatically loaded by the Gemini CLI at startup to inherit the exact context, memory, and state of our development sessions.

## 🚀 Active Environment & Services
- **Angular Frontend:** Port 4200 (Running in the background via container PID, compiled with native Zoneless change detection).
- **FastAPI Backend:** Port 5000 (Running in the background via container PID with auto-reload).
- **PostgreSQL 17 Database:** Port 5432 (pgvector enabled).
- **Redis Broker:** Port 6379 (Broker for Celery and WebSockets).

## 🔐 Login Credentials (Database Seeded)
- **Administrator Email:** admin@referat.io
- **Password:** admin_secure_pass_change_me
- *Note:* Do NOT use .local domains (e.g. admin@referat.local) as Pydantic's strict EmailStr validator rejects them under RFC 6762 guidelines (reserved/multicast DNS domain names).

## 🧠 Celery Workers & ML Volume Mounts
- **Celery Command:** .venv/bin/celery -A app.tasks worker --loglevel=info
- **Native Volumes:** Docker Compose natively mounts the host's compiled models directory (/home/christian/StyrPaa/MinRapport/møder/pipeline/models:/workspace/pipeline/models) and transscribe to bypass broken absolute symlinks inside containerized environments.
- **State:** Meeting ID 1 (2026-07-17 08-47-17.mp4) is currently in processing status, executing the pipeline (Whisper/Gemma) asynchronously in the background.

## 🛠 Completed Milestones
All 15 project phases are completed with 100% success. Release 2026.07.22 is fully built, tested, and published to GHCR.
