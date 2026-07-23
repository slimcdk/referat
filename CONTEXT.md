# Referat - System Context & Domain Language

This document defines the core domain model, ubiquitous language, and technical context for the Referat workspace.

## Ubiquitous Language

*   **Møde (Meeting)**: An overall event or container representing a full session. It holds metadata (Title, Date, Status), an aggregated final summary (consisting of master decisions, action items, and `referat.md`), and groups one or more clips.
*   **Klip (MeetingClip)**: An individual video/audio recording file uploaded under a Meeting. It is processed independently via its own execution pipeline, producing its own raw transcript, clean transcript, and duration metrics.
*   **Segment (MeetingChunk)**: A 4-sentence dense text slice extracted from a clip's transcript, coupled with a 384-dimensional vector embedding for semantic search.
*   **Fælles Referat (Aggregated Summary)**: A consolidated markdown document and structured dataset synthesized by combining and chronologically aligning all completed clip transcripts under a meeting, processed by the local Gemma LLM.

## System Architecture

The application is structured as a decoupled multi-service system:

```
┌────────────────────────────────────────────────────────┐
│                        Frontend                        │
│             Angular, Standalone, Zoneless              │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ REST / WebSockets (Port 5000)
                           ▼
┌────────────────────────────────────────────────────────┐
│                        Backend                         │
│                    FastAPI, Alembic                    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ├─────────────────────────────┐
                           ▼                             ▼
┌────────────────────────────────────────────────────────┐ ┌───────────────────┐
│                     Task Worker                        │ │     Database      │
│                     Celery, Redis                      │ │   PostgreSQL 17   │
└──────────────────────────┬─────────────────────────────┘ │    (pgvector)     │
                           │                               └───────────────────┘
                           ▼ Subprocess
┌────────────────────────────────────────────────────────┐
│                      ML Pipeline                       │
│        faster-whisper, PyTorch, SentenceTransformer    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼ CDP Bridge
┌────────────────────────────────────────────────────────┐
│                      Ollama Host                       │
│                       Gemma3:4b                        │
└────────────────────────────────────────────────────────┘
```

## Core Workflows

1.  **Creation**: Users create a new `Meeting` in the dashboard card layout.
2.  **Upload**: Users choose a meeting and upload one or more `MeetingClip`s. Files are transferred in robust 5MB chunk HTTP posts.
3.  **Analysis**: Users explicitly trigger "Behandl klip" on pending clips. The Celery worker invokes the Whisper pipeline, producing a transcript and populating `pgvector` chunks.
4.  **Consolidation**: Users click "Generer Fælles Referat". The worker offsets clip tids, concatenates transcripts, and asks Gemma to generate a consolidated master meeting summary.
