import asyncio
import os
import json
import shutil
import time
import subprocess
import redis
from celery import shared_task
from sqlalchemy.future import select
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.meeting import Meeting
from app.models.meeting_clip import MeetingClip
from app.models.job_metrics import JobMetrics
from app.models.action_item import ActionItem
from app.models.decision import Decision
from app.models.meeting_chunk import MeetingChunk

# Model name for 384-dimensional sentence embeddings
MODEL_NAME = "all-MiniLM-L6-v2"

def publish_progress(meeting_id: int, status: str, progress: int):
    try:
        r = redis.from_url(settings.REDIS_URL)
        channel_name = f"meeting_progress_{meeting_id}"
        message = json.dumps({
            "meeting_id": meeting_id,
            "status": status,
            "progress": progress
        })
        r.publish(channel_name, message)
        r.close()
        print(f"Published progress update for meeting {meeting_id}: {status} ({progress}%)")
    except Exception as e:
        print(f"Failed to publish progress to Redis: {str(e)}")

def publish_clip_progress(clip_id: int, status: str, progress: int):
    try:
        r = redis.from_url(settings.REDIS_URL)
        channel_name = f"clip_progress_{clip_id}"
        message = json.dumps({
            "clip_id": clip_id,
            "status": status,
            "progress": progress
        })
        r.publish(channel_name, message)
        r.close()
        print(f"Published clip progress update for clip {clip_id}: {status} ({progress}%)")
    except Exception as e:
        print(f"Failed to publish clip progress to Redis: {str(e)}")

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        return asyncio.run_coroutine_threadsafe(coro, loop).result()
    else:
        return loop.run_until_complete(coro)

# 1. Celery tasks definitions
@shared_task(name="app.tasks.meeting_pipeline.analyze_clip_task")
def analyze_clip_task(clip_id: int):
    return run_async(async_analyze_clip(clip_id))

@shared_task(name="app.tasks.meeting_pipeline.aggregate_meeting_task")
def aggregate_meeting_task(meeting_id: int):
    return run_async(async_aggregate_meeting(meeting_id))

# 2. Async single clip processing logic
async def async_analyze_clip(clip_id: int):
    async with async_session_maker() as session:
        # Fetch clip record
        result = await session.execute(select(MeetingClip).filter(MeetingClip.id == clip_id))
        clip = result.scalars().first()
        if not clip:
            print(f"Clip with ID {clip_id} not found.")
            publish_clip_progress(clip_id, "failed", 0)
            return False

        # Set clip status to processing
        clip.status = "processing"
        await session.commit()
        publish_clip_progress(clip_id, "processing", 10)
        publish_progress(clip.meeting_id, "processing_clips", 30)

        start_time = time.time()
        print(f"Starting ML pipeline execution for clip: {clip.title}")

        try:
            # Setup paths
            pipeline_dir = "/workspace/pipeline"
            python_exec = os.path.join(pipeline_dir, ".venv", "bin", "python")
            script_path = os.path.join(pipeline_dir, "process_meeting.py")
            rec_path = clip.file_path

            # State: Transcribing (20%)
            publish_clip_progress(clip_id, "transcribing", 20)

            # Invoke process_meeting.py for this specific clip file
            # --skip-video can be added if we only want audio processing, but we support both
            cmd = [python_exec, script_path, rec_path]
            print(f"Executing command: {' '.join(cmd)}")
            
            proc = subprocess.run(
                cmd,
                cwd=pipeline_dir,
                capture_output=True,
                text=True
            )

            if proc.returncode != 0:
                print(f"Pipeline subprocess failed with returncode {proc.returncode}")
                print(f"STDOUT: {proc.stdout}")
                print(f"STDERR: {proc.stderr}")
                publish_clip_progress(clip_id, "failed", 0)
                raise Exception(f"ML Pipeline script failed: {proc.stderr}")

            # State: Summarizing (70%)
            publish_clip_progress(clip_id, "summarizing", 70)

            # Read output files
            base_name = os.path.splitext(os.path.basename(rec_path))[0]
            output_dir = os.path.join(pipeline_dir, "output", base_name)

            transcript_raw_path = os.path.join(output_dir, "transcript.txt")
            transcript_clean_path = os.path.join(output_dir, "transcript_clean.txt")
            if not os.path.exists(transcript_clean_path):
                transcript_clean_path = transcript_raw_path # Fallback

            referat_path = os.path.join(output_dir, "referat.md")

            with open(transcript_raw_path, "r", encoding="utf-8") as f:
                clip.transcript_raw = f.read()

            with open(transcript_clean_path, "r", encoding="utf-8") as f:
                clip.transcript_clean = f.read()

            if os.path.exists(referat_path):
                with open(referat_path, "r", encoding="utf-8") as f:
                    clip.summary = f.read()

            # State: Indexing and embedding (85%)
            publish_clip_progress(clip_id, "indexing", 85)

            # Load SentenceTransformer and generate embeddings specifically for this clip's chunks
            print(f"Loading SentenceTransformer for clip indexing: {MODEL_NAME}")
            model = SentenceTransformer(MODEL_NAME)

            sentences = clip.transcript_clean.split(".")
            chunk_size = 4
            chunks = []
            
            for i in range(0, len(sentences), chunk_size):
                chunk_text = ". ".join(sentences[i:i+chunk_size]).strip()
                if chunk_text:
                    chunks.append(chunk_text)

            if chunks:
                print(f"Generating embeddings for {len(chunks)} clip transcript chunks...")
                embeddings = model.encode(chunks)

                for idx, chunk_text in enumerate(chunks):
                    db_chunk = MeetingChunk(
                        meeting_id=clip.meeting_id,
                        clip_id=clip_id,
                        start_time=float(idx * 30), # Approx estimation
                        end_time=float((idx + 1) * 30),
                        text=chunk_text,
                        embedding=embeddings[idx].tolist()
                    )
                    session.add(db_chunk)

            # Set clip status to completed
            clip.status = "completed"
            
            # Save metrics
            total_duration = time.time() - start_time
            clip.duration = total_duration
            
            await session.commit()
            publish_clip_progress(clip_id, "completed", 100)
            publish_progress(clip.meeting_id, "clip_processed", 100)
            
            print(f"Successfully processed clip ID {clip_id} in {total_duration:.2f} seconds.")
            return True

        except Exception as e:
            print(f"Error executing ML pipeline on clip: {str(e)}")
            clip.status = "failed"
            await session.commit()
            publish_clip_progress(clip_id, "failed", 0)
            raise e

# 3. Async multiple clips aggregation logic
async def async_aggregate_meeting(meeting_id: int):
    async with async_session_maker() as session:
        # Fetch the meeting record
        result = await session.execute(select(Meeting).filter(Meeting.id == meeting_id))
        meeting = result.scalars().first()
        if not meeting:
            print(f"Meeting with ID {meeting_id} not found.")
            publish_progress(meeting_id, "failed", 0)
            return False

        # Set status to processing
        meeting.status = "processing"
        await session.commit()
        publish_progress(meeting_id, "aggregating", 10)

        start_time = time.time()
        print(f"Starting meeting aggregation for meeting: {meeting.title}")

        try:
            # Fetch all completed clips for this meeting sorted by sequence number
            stmt = select(MeetingClip).filter(
                MeetingClip.meeting_id == meeting_id,
                MeetingClip.status == "completed"
            ).order_by(MeetingClip.sequence_number)
            
            clips_result = await session.execute(stmt)
            clips = clips_result.scalars().all()
            
            if not clips:
                print(f"No completed clips found for meeting {meeting_id} to aggregate.")
                meeting.status = "pending"
                await session.commit()
                publish_progress(meeting_id, "failed", 0)
                return False

            # Setup paths for aggregate script
            pipeline_dir = "/workspace/pipeline"
            python_exec = os.path.join(pipeline_dir, ".venv", "bin", "python")
            script_path = os.path.join(pipeline_dir, "aggregate.py")
            
            # List of clip directories (their filenames without ext)
            clip_dirs = [os.path.splitext(os.path.basename(c.file_path))[0] for c in clips]

            publish_progress(meeting_id, "aggregating", 40)

            # Invoke pipeline/aggregate.py
            cmd = [python_exec, script_path, str(meeting_id), meeting.title] + clip_dirs
            print(f"Executing aggregation command: {' '.join(cmd)}")
            
            proc = subprocess.run(
                cmd,
                cwd=pipeline_dir,
                capture_output=True,
                text=True
            )

            if proc.returncode != 0:
                print(f"Aggregation subprocess failed with returncode {proc.returncode}")
                print(f"STDOUT: {proc.stdout}")
                print(f"STDERR: {proc.stderr}")
                publish_progress(meeting_id, "failed", 0)
                raise Exception(f"Aggregation script failed: {proc.stderr}")

            publish_progress(meeting_id, "finalizing", 80)

            # Read back aggregated outputs
            output_dir = os.path.join(pipeline_dir, "output", f"meeting_{meeting_id}")
            referat_path = os.path.join(output_dir, "referat.md")
            meeting_json_path = os.path.join(output_dir, "meeting.json")

            # Load synthesized summary
            with open(referat_path, "r", encoding="utf-8") as f:
                meeting.summary = f.read()

            # Concatenate individual clip transcripts for global transcript fields
            meeting.transcript_raw = "\n\n".join(f"=== {c.title} ===\n{c.transcript_raw}" for c in clips)
            meeting.transcript_clean = "\n\n".join(f"=== {c.title} ===\n{c.transcript_clean}" for c in clips)

            # Parse master decisions and action items
            if os.path.exists(meeting_json_path):
                with open(meeting_json_path, "r", encoding="utf-8") as f:
                    meeting_data = json.load(f)

                # Clear old decisions and action items for this meeting to prevent duplicates
                await session.execute(Decision.__table__.delete().where(Decision.meeting_id == meeting_id))
                await session.execute(ActionItem.__table__.delete().where(ActionItem.meeting_id == meeting_id))

                structured = meeting_data.get("structured", {})

                # Save Decisions
                for dec_text in structured.get("beslutninger", []):
                    db_dec = Decision(meeting_id=meeting_id, decision=dec_text)
                    session.add(db_dec)

                # Save Action Items
                for item in structured.get("opgaver", []):
                    db_item = ActionItem(
                        meeting_id=meeting_id,
                        task=item.get("opgave", ""),
                        assignee=item.get("ansvarlig"),
                        deadline=item.get("deadline")
                    )
                    session.add(db_item)

            # Save metrics
            total_duration = time.time() - start_time
            
            # Remove old metrics if exist
            await session.execute(JobMetrics.__table__.delete().where(JobMetrics.meeting_id == meeting_id))
            
            db_metrics = JobMetrics(
                meeting_id=meeting_id,
                video_length=sum(c.duration or 0.0 for c in clips),
                total_processing_time=total_duration,
                transcription_time=total_duration * 0.2, # Aggregation estimate placeholders
                ocr_time=0.0,
                summarization_time=total_duration * 0.8
            )
            session.add(db_metrics)

            # Set status to completed
            meeting.status = "completed"
            await session.commit()
            
            publish_progress(meeting_id, "completed", 100)
            print(f"Successfully aggregated meeting ID {meeting_id} in {total_duration:.2f} seconds.")
            return True

        except Exception as e:
            print(f"Error executing meeting aggregation: {str(e)}")
            meeting.status = "failed"
            await session.commit()
            publish_progress(meeting_id, "failed", 0)
            raise e
