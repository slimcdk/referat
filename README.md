# Referat 📝

A self-hosted, full-stack web application designed to process, analyze, and manage your meeting and conversation recordings (both video and audio) locally. 

By wrapping your local media processing scripts, Referat runs an asynchronous machine learning pipeline to transcribe speech, perform visual keyframe analysis (OCR, slide detection), and generate structured summaries (action items, decisions, and topics).

## Features
- Secure Media Ingestion: JWT-secured web interface with chunked uploads to safely process multi-gigabyte video/audio files.
- Asynchronous Task Queue: Powered by Celery and Redis to run heavy ML workloads (transcription, vision) in the background.
- Smart Progress Tracking: Real-time progress updates and status bars via WebSockets.
- Semantic & Text Search: Deep search within your meeting history using PostgreSQL and pgvector for vector embeddings.
- Global Speaker Management: Diarization dashboard where you can play identified voiceprints across meetings and assign real names.
- Seamless AI Agents (MCP): Integrated Model Context Protocol (MCP) server allowing tools like Claude Desktop or Gemini to seamlessly query your meeting database.

## Tech Stack
- Frontend: Angular (latest) and Angular Material (with Light/Dark mode)
- Backend: Python FastAPI
- Background Tasks: Celery and Redis
- Database: PostgreSQL (with pgvector extension)
- ML Engine: local Ollama (Gemma3) and faster-whisper

## Getting Started (Development)

This repository includes a fully-configured VS Code Devcontainer to make setup incredibly simple.

### Prerequisites
- VS Code with the Dev Containers extension installed
- Docker running on your host machine

### Setup Instructions
1. Open the project folder in VS Code:

    code /home/christian/Projects/referat

2. When prompted by VS Code, click 'Reopen in Container' (or open the Command Palette via F1 and select 'Dev Containers: Reopen in Container').
3. Once the container starts, open an integrated terminal inside VS Code and spin up the database and Redis services:

    docker compose up -d

4. The devcontainer automatically forwards port 4200 (Angular) and port 5000 (FastAPI) to your host machine.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
