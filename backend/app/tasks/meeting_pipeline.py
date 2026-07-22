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
        print(f"Published progress update: {status} ({progress}%)")
    except Exception as e:
        print(f"Failed to publish progress to Redis: {str(e)}")

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

@shared_task(name="app.tasks.meeting_pipeline.analyze_meeting_task")
def analyze_meeting_task(meeting_id: int):
    return run_async(async_analyze_meeting(meeting_id))

async def async_analyze_meeting(meeting_id: int):
    async with async_session_maker() as session:
        # 1. Fetch the meeting record
        result = await session.execute(select(Meeting).filter(Meeting.id == meeting_id))
        meeting = result.scalars().first()
        if not meeting:
            print(f"Meeting with ID {meeting_id} not found.")
            publish_progress(meeting_id, "failed", 0)
            return False

        # Set status to processing
        meeting.status = "processing"
        await session.commit()
        publish_progress(meeting_id, "processing", 10)

        start_time = time.time()
        print(f"Starting ML pipeline execution for meeting: {meeting.title}")

        try:
            # 2. Setup paths and python interpreter for the pipeline
            pipeline_dir = "/workspace/pipeline"
            python_exec = os.path.join(pipeline_dir, ".venv", "bin", "python")
            script_path = os.path.join(pipeline_dir, "process_meeting.py")
            rec_path = meeting.file_path

            # State: Transcribing (20%)
            publish_progress(meeting_id, "transcribing", 20)

            # Invoke process_meeting.py
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
                publish_progress(meeting_id, "failed", 0)
                raise Exception(f"ML Pipeline script failed: {proc.stderr}")

            # State: Summarizing (70%)
            publish_progress(meeting_id, "summarizing", 70)

            print("ML pipeline subprocess execution completed successfully!")

            # 3. Read generated output files from pipeline
            base_name = os.path.splitext(os.path.basename(rec_path))[0]
            output_dir = os.path.join(pipeline_dir, "output", base_name)

            transcript_raw_path = os.path.join(output_dir, "transcript.txt")
            transcript_clean_path = os.path.join(output_dir, "transcript_clean.txt")
            if not os.path.exists(transcript_clean_path):
                transcript_clean_path = transcript_raw_path # Fallback

            referat_path = os.path.join(output_dir, "referat.md")
            meeting_json_path = os.path.join(output_dir, "meeting.json")

            # Load file contents
            with open(transcript_raw_path, "r", encoding="utf-8") as f:
                meeting.transcript_raw = f.read()

            with open(transcript_clean_path, "r", encoding="utf-8") as f:
                meeting.transcript_clean = f.read()

            with open(referat_path, "r", encoding="utf-8") as f:
                meeting.summary = f.read()

            # 4. Parse meeting.json for action items and decisions
            if os.path.exists(meeting_json_path):
                with open(meeting_json_path, "r", encoding="utf-8") as f:
                    meeting_data = json.load(f)

                # Save Decisions
                for dec_text in meeting_data.get("decisions", []):
                    db_dec = Decision(meeting_id=meeting_id, decision=dec_text)
                    session.add(db_dec)

                # Save Action Items
                for item in meeting_data.get("action_items", []):
                    db_item = ActionItem(
                        meeting_id=meeting_id,
                        task=item.get("task", ""),
                        assignee=item.get("assignee"),
                        deadline=item.get("deadline")
                    )
                    session.add(db_item)

            # State: Indexing and embedding (85%)
            publish_progress(meeting_id, "indexing", 85)

            # 5. Load SentenceTransformer and generate pgvector embeddings
            print(f"Loading SentenceTransformer: {MODEL_NAME}")
            model = SentenceTransformer(MODEL_NAME)

            # Segment transcript into 4-sentence chunks
            sentences = meeting.transcript_clean.split(".")
            chunk_size = 4
            chunks = []
            
            for i in range(0, len(sentences), chunk_size):
                chunk_text = ". ".join(sentences[i:i+chunk_size]).strip()
                if chunk_text:
                    chunks.append(chunk_text)

            if chunks:
                print(f"Generating embeddings for {len(chunks)} transcript chunks...")
                embeddings = model.encode(chunks)

                for idx, chunk_text in enumerate(chunks):
                    db_chunk = MeetingChunk(
                        meeting_id=meeting_id,
                        start_time=float(idx * 30), # Approx timeline estimation
                        end_time=float((idx + 1) * 30),
                        text=chunk_text,
                        embedding=embeddings[idx].tolist()
                    )
                    session.add(db_chunk)

            # 6. Record Job Metrics
            total_duration = time.time() - start_time
            video_len = 0.0 # Standard fallback
            
            db_metrics = JobMetrics(
                meeting_id=meeting_id,
                video_length=video_len,
                total_processing_time=total_duration,
                transcription_time=total_duration * 0.5, # Estimation placeholders
                ocr_time=total_duration * 0.2,
                summarization_time=total_duration * 0.3
            )
            session.add(db_metrics)

            # Set status to completed and persist
            meeting.status = "completed"
            await session.commit()
            
            # State: Completed (100%)
            publish_progress(meeting_id, "completed", 100)
            
            print(f"Successfully processed meeting ID {meeting_id} in {total_duration:.2f} seconds.")
            return True

        except Exception as e:
            print(f"Error executing ML pipeline: {str(e)}")
            meeting.status = "failed"
            await session.commit()
            publish_progress(meeting_id, "failed", 0)
            raise e
