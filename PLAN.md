# Referat - Implementation Plan

## Objective
Build a fully-fledged, self-hosted web application for meeting analysis. The new platform will build upon the existing core ML logic. It will handle video uploads, execute the ML pipeline asynchronously, store structured data for robust search/querying, and expose an MCP server interface for external LLMs.

## Architecture Stack
- Frontend: Angular (latest) with Angular Material for a clean, responsive UI, including built-in support for Light/Dark mode toggling. All UI text, documentation, and codebase comments MUST be in English.
- Backend / API: Python (FastAPI). Chosen for native integration with the existing ML scripts, async support, and rapid API development.
- Real-time Communication: WebSockets (FastAPI + Angular) for streaming real-time ML pipeline progress updates (e.g., "Transcribing...", "Summarizing...", "Done").
- Task Queue: Celery + Redis. Essential for offloading heavy audio/video processing from the web server to background workers.
- Database: PostgreSQL with pgvector. Handles application metadata (status, tags), structured meeting outputs (action items, decisions), and vector embeddings for semantic search.
- Storage Abstraction (S3 / Local): Implemented to allow distributed deployments. Large files (video, audio) are stored via an S3-compatible API. This allows the core services (API, DB, Storage) to run on a low-compute NAS, while heavy GPU ML workers run on a separate Desktop, pulling and pushing data via S3.
- AI Integration: Python MCP (Model Context Protocol) server integrated into the backend, allowing local models (Ollama) or external LLMs (Claude/Gemini) to seamlessly query the meeting corpus.

## System Workflow
1. Deployment Flexibility: The system supports both a distributed mode (Core API/DB/S3 on NAS; Celery GPU workers on Desktop) and a unified mode (All-in-one container for easy local execution).
2. Ingestion: User uploads a screen recording (e.g., .mp4) or audio recording (e.g., .wav, .m4a) via the Angular UI. FastAPI saves the file to the configured Storage backend (S3 or local volume) and queues a job in Celery.
3. Processing & Updates: A Celery worker (potentially running on a remote machine) picks up the job, downloads the video from Storage, and runs the existing process_meeting.py logic. As it progresses through transcription, OCR, and summarization, it updates its status in Redis.
4. Real-Time Sync: FastAPI listens for status changes (via Redis Pub/Sub) and broadcasts updates over WebSockets to the Angular client.
5. Storage: Once the pipeline completes, the structured output (meeting.json, referat.md) and generated embeddings are persisted into PostgreSQL.
6. Consumption: The user can view the meeting, search the corpus via the UI, or use an MCP-compatible AI agent to ask questions across all meeting histories.

## Phased Implementation Plan

### Phase 1: Environment Setup & Infrastructure (Initial Commit)
- Project Initialization: Create the new project repository in /home/christian/Projects/referat and initialize Git.
- Version Control Config: Generate a comprehensive .gitignore using Toptal's gitignore API (for Python, Node, Angular, etc.) and add project-specific ignores. Create a .gitattributes file.
- AI Agent Context: Create an AGENTS.md file containing a detailed description of the project, architecture, and coding standards to provide context for AI tools.
- VS Code Devcontainer: Create a .devcontainer setup configured for Python and Node.js development. Include all necessary CLI tools (devcontainer CLI, pytest, jest, playwright, etc.). Map local ~/.gemini and ~/.claude directories into the container and automatically install relevant VS Code extensions (e.g., Claude Dev, GitHub Copilot).
- Initial Verification: Build the devcontainer using the devcontainer CLI to ensure it starts correctly, then commit this entire base environment to Git before proceeding.
- Core Infrastructure: Create docker-compose.yml in the root for local development (PostgreSQL + pgvector and Redis). For production deployment, keep a separate docker-compose.prod.yml inside a deploy/ directory to avoid conflicts. Integrate Alembic for database migrations and define local storage directories.
- Code Quality & Pre-commit Hooks: Set up husky (Angular) and pre-commit (Python) for automated linting.
- Security & Authentication: Implement JWT-based email and password authentication. Store user credentials securely (hashed) in the PostgreSQL database.
- Ensure all configuration and secrets are managed via environment variables.

### Phase 2: Foundation (App) & Core Data Models
- Initialize the Angular project with Angular Material.
- Set up FastAPI base structure.
- Define SQLAlchemy ORM models for User, Meeting, ActionItem, Decision, MeetingChunk, Settings, JobMetrics, and Speaker.
- Implement FastAPI endpoints for user registration/login (JWT issuance).
- Chunked Uploads: Implement secure chunked file uploads in FastAPI and the Angular upload component to safely handle multi-gigabyte video files without triggering OOM errors.

### Phase 3: Background Workers & Pipeline Integration
- Import and wrap the existing pipeline/ scripts to function as Celery tasks.
- Implement Celery task routing for the meeting analysis pipeline.
- Task Failure Handling: Implement a dead-letter queue mechanism in Celery to catch and handle GPU OOM errors, timeouts, or unexpected crashes. Allow users to resume or restart failed analyses without re-uploading the source media.
- Advanced Screen Sharing Intelligence: Enhance the vision pipeline (Gemma/Ollama) to perform multimodal correlation. The engine must explicitly track mouse pointers/cursors and correlate on-screen visual elements (slides, code, diagrams) with the concurrent audio transcript to generate context-aware annotations.
- Metrics Collection: Instrument the Celery tasks to record detailed execution times for each ML stage (transcription, OCR, summarization) to calculate historical processing speeds.
- Ensure GPU/CPU hardware constraints are respected by the worker processes, dynamically loading the LLM model size configured by the user.

### Phase 4: Real-time WebSockets
- Implement WebSocket endpoints in FastAPI.
- Set up a Redis Pub/Sub mechanism so Celery workers can publish progress events.
- Implement an Angular WebSocket service to consume events and update the UI progress bars in real-time.

### Phase 5: UI Dashboards, Search & Settings
- Build the Angular Meeting Dashboard to display the timeline, video/audio player, and the generated summary. The transcript and summary MUST include speaker identification (diarization), so users can see exactly who said what.
- Interactive Visual Timeline: The dashboard will display keyframes side-by-side with the transcript. When the user speaks about a specific on-screen element (or points to it with the mouse during a screen share), the UI will highlight or jump to the relevant correlated visual context.
- Global Speaker Management UI: Create a dedicated interface mapping to the diarization engine. Users can view a list of unique voiceprints identified across all meetings, listen to short generated audio snippets for each, and assign real names (e.g., mapping "SPEAKER_01" to "Christian"). This globally updates future and past meeting transcripts.
- Smart Upload UI: When uploading a new meeting, use the historical JobMetrics data to display an intelligent Estimated Time of Arrival (ETA) for the analysis.
- Settings Interface: Create a configuration page where users can select the size of the LLM models based on their compute resources. Include Data Retention settings to automatically delete raw .mp4 files from storage after X days to save space, while preserving the text transcripts and vector embeddings permanently.
- Implement full-text and semantic search queries in PostgreSQL using pgvector.
- Create a search interface in the frontend.

### Phase 6: MCP & API Integration for Coding Agents
- Integrate an MCP Server within the Python backend (using the official Python MCP SDK) and expose a robust REST API.
- Expose tools like search_meetings, get_action_items, and get_meeting_summary so that coding agents (Claude, Gemini, Cursor, etc.) can extract meeting intelligence.
- Seamless Agent Access: The MCP server and API will authenticate via a long-lived Personal Access Token (PAT) tied to a user account. This PAT can be configured in agent configurations (e.g., claude_desktop_config.json), ensuring prompts like "extract the architecture decisions from today's meeting" work instantly for the AI without needing manual web login.

## Frontend Testing Strategy
To ensure a robust and maintainable UI, frontend testing will be implemented in two distinct layers:

1. Component & Unit Testing (Jest):
    - Setup: We will replace Angular's default Karma/Jasmine runner with Jest. Jest is significantly faster, runs in a Node environment, and is the industry standard.
    - Scope: We will write .spec.ts files for individual Angular Components, Services, and Pipes.
    - Execution: Run locally via npm run test and automatically on every GitHub Actions PR.

2. End-to-End (E2E) Testing (Playwright):
    - Setup: We will install Playwright (npm init playwright@latest) alongside the Angular project.
    - Scope: Playwright will spin up a real headless browser and execute the core User Journeys:
        - Journey 1 (Upload): Authenticate -> Navigate to Upload -> Select File -> Assert WebSocket progress bar updates -> Assert redirect to Dashboard.
        - Journey 2 (Search): Navigate to Dashboard -> Enter query -> Assert correct semantic search results from the database.
        - Journey 3 (Settings): Navigate to Settings -> Change LLM model size -> Assert settings are saved and persisted.
    - Execution: Run locally via npx playwright test and automatically in GitHub Actions.

3. Test Data Strategy (Deterministic Testing):
    - To ensure E2E tests are stable and reliable, we will never test against a live or empty database.
    - We will create a seed.sql or Python seeding script that populates the PostgreSQL test database with deterministic data.
    - Git LFS for Binary Test Data: Any large binary files required for testing (e.g., short dummy .mp4 video files) will be tracked using Git Large File Storage (Git LFS).
    - Playwright tests will assert against this known state.

## Development Rules for AI Agents
1. Permanent Tests Only: Test files (Jest and Playwright) must ALWAYS be created in their permanent directory structures (e.g., e2e/tests/). Temporary scripts or disposable test files are strictly forbidden.
2. Definition of Done: A feature is not complete until both its application code AND its corresponding test code have been written to the file system, passed execution, and are ready for a Git commit.

## Verification, Testing & Open Source Readiness
- Backend Unit Testing: Implement tests using pytest to cover FastAPI endpoints, database operations, and Celery task logic.
- Frontend Unit & Component Testing: Configure Jest to test Angular components, services, and WebSocket interaction logic in isolation.
- Frontend End-to-End (E2E) Testing: Implement Playwright to simulate user workflows to ensure the integrated system works from the user's perspective.
- CI Workflows: Set up GitHub Actions to automatically run backend and frontend test suites on every pull request.
- Documentation: Write generic, open-source friendly README and setup guides, omitting any personal data or specific local paths.
- Functional Verification:
    - Verify file uploads handle large files smoothly.
    - Confirm Celery workers successfully execute the ML models without blocking the FastAPI server.
    - Test WebSocket reconnections and real-time state consistency.
    - Validate pgvector semantic search accuracy with sample queries.
    - Ensure MCP tools return properly formatted JSON for external LLMs.
