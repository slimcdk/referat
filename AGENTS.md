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

### Frontend Design & UX Guidelines
- **Pure Top-Nav Layout**: The application must not use sidebars, drawers, or collapsible side menus. All routing, navigation, and utilities must be placed inside the global top navbar.
- **Thematic Colors (Material 3)**: Utilize official Angular Material 3 design tokens (`--mat-sys-*`) for styling backgrounds, borders, and typography. The primary brand colors are Cyan (`mat.$cyan-palette`) and Orange (`mat.$orange-palette`) for tertiary accents.
- **Interactive Hover-Expanding Buttons**: ALL buttons containing a `mat-icon` and text must be styled with the global `.action-btn` class. By default, they must appear as icon-only circles (`width: 38px`), sliding open elegantly into a pill shape (`width: 135px`, or custom widths like `140px` for GitHub) on mouse hover to reveal the inner text wrapped in `.btn-text`.
- **Zoneless & Signals Compatibility**: Because the frontend uses Zoneless change detection, all asynchronous properties (especially HTTP subscriptions or dynamic updates) must be bound using Angular Signals (`signal()`) to notify change detection natively.

## Agent skills

### Issue tracker

Issues and PRDs live in the repository's GitHub Issues (uses the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Using the default triage label vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context documentation layout. See `docs/agents/domain.md`.

