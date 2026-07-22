# Referat - AI Agent Workspace Context

This file provides system context for AI coding agents (such as Claude, Gemini, or Cursor) working on the "Referat" project.

## Project Description
"Referat" is a self-hosted full-stack web application designed to process, analyze, and manage meeting recordings (video and audio). It executes an asynchronous machine learning pipeline to transcribe speech, perform visual keyframe analysis (OCR, slide detection), and compile structured summaries (action items, decisions, topics).

## Architecture Stack
- Frontend: Angular (latest) with Angular Material. Connects to backend via REST and WebSockets. Built-in support for Light/Dark mode.
- Backend: Python FastAPI. Secured by JWT-based authentication for the web UI and Personal Access Tokens (PAT) for external APIs.
- Task Queue: Celery + Redis for asynchronous background processing of heavy audio/video pipelines.
- Database: PostgreSQL with pgvector for storing metadata, transcripts, structured summaries, and semantic vector embeddings.
- Storage: S3-compatible API or Local Storage abstraction to support distributed deployments (e.g., core server on NAS, GPU workers on desktop).
- MCP Server: Built into FastAPI (using Python MCP SDK) to let local/remote LLM agents query meeting data seamlessly.

## Key Features
1. Secure Ingestion: JWT authentication and chunked uploads for large video/audio files (no memory exhaustion).
2. Real-time Progress: WebSockets providing step-by-step progress of the Celery pipeline.
3. Multimodal Screen Sharing: Vision tracking of mouse pointers and correlating screen visuals (slides, code) with spoken context.
4. Global Speaker Management: Diarization dashboard where users can view, play audio snippets of, and name identified voiceprints globally.
5. Smart Upload ETA: Estimates analysis time based on historical execution metrics.

## Development Standards & Hygiene
- Testing Requirements:
  - Backend: pytest covering API and Celery workers.
  - Frontend Unit: Jest (preferred over Karma).
  - Frontend E2E: Playwright executing core user journeys against mock seeded databases.
- Code Quality: Automated linting via Git hooks: Husky (frontend) and pre-commit (backend).
- Git Hygiene: No temporary test files; keep tests in permanent folders (like e2e/tests/) and unit tests next to source files.
