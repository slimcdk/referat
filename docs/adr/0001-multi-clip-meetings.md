# ADR 1: Multi-Clip Meeting Architecture

## Status
Accepted

## Context
Originally, the "Referat" application mapped one meeting directly to a single video/audio recording. The ML pipeline (`process_meeting.py`) transcribed, extracted keyframes, and summarized that single file. 
However, in real-world scenarios, a single physical meeting is often captured across multiple consecutive screen shares, files, or clips. The user requested the ability to upload multiple separate clips under a single meeting, manage and process them individually, and subsequently aggregate their transcripts and summaries into a consolidated joint meeting summary.

## Decisions
We decided to shift from a 1:1 meeting-to-file mapping to a 1:N meeting-to-clips mapping:

1.  **Database Separation**:
    *   Created a new `MeetingClip` table storing `id`, `meeting_id`, `file_path`, `sequence_number`, `status`, `duration`, `transcript_raw`, `transcript_clean`, and clip-level `summary`.
    *   Made `file_path` on the `Meeting` table optional/nullable to support backwards compatibility while facilitating empty or multi-clip meetings.
    *   Added a nullable `clip_id` column to `MeetingChunk` to support clip-level search context while retaining global meeting correlation.

2.  **Explicit, Granular Processing**:
    *   Clips are uploaded under a meeting but are not processed automatically.
    *   A "Process Clip" action was introduced to trigger the standard Whisper + Keyframe pipeline (`analyze_clip_task`) for that specific file. This enables granular processing without restarting the entire meeting pipeline.

3.  **Aggregated Summary Generation**:
    *   Introduced an overall meeting status and an "Aggregate / Generate Joint Summary" action.
    *   Created `pipeline/aggregate.py` to compile segments and visuals across completed clips, offset timestamps chronologically, and execute the standard `summarize` function.
    *   This generates a consolidated `referat.md` and parsed decisions/action items for the parent `Meeting` record.

## Consequences
*   **Encapsulation**: Keeps heavy ML dependencies confined to the pipeline environment, while the FastAPI backend handles light metadata and task triggers.
*   **Scalability**: Allows users to incrementally add clips to active meetings and run expensive ML processes only on newly uploaded clips.
*   **Continuity**: Restructuring transcripts dynamically ensures semantic search queries correctly match segment timestamps relative to the aggregated timeline.
