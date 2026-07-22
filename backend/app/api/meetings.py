import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.meeting import Meeting
from app.schemas.meeting import ChunkUploadResponse, CompleteUploadResponse, MeetingOut
from app.tasks.meeting_pipeline import analyze_meeting_task

router = APIRouter(prefix="/meetings", tags=["meetings"])

# Storage directory setups
TEMP_DIR = os.path.join(settings.LOCAL_STORAGE_DIR, "temp")
MEETINGS_DIR = os.path.join(settings.LOCAL_STORAGE_DIR, "meetings")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(MEETINGS_DIR, exist_ok=True)

@router.post("/upload/chunk", response_model=ChunkUploadResponse)
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    # Unique directory for this specific upload
    chunk_dir = os.path.join(TEMP_DIR, upload_id)
    os.makedirs(chunk_dir, exist_ok=True)
    
    chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index}")
    
    # Save chunk to disk
    with open(chunk_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {
        "status": "success",
        "message": f"Chunk {chunk_index} uploaded successfully.",
        "chunk_index": chunk_index
    }

@router.post("/upload/complete", response_model=CompleteUploadResponse)
async def complete_upload(
    upload_id: str = Form(...),
    title: str = Form(...),
    filename: str = Form(...),
    total_chunks: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chunk_dir = os.path.join(TEMP_DIR, upload_id)
    
    if not os.path.exists(chunk_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chunks found for this upload ID."
        )
        
    # Verify we have all chunks
    for i in range(total_chunks):
        chunk_file = os.path.join(chunk_dir, f"chunk_{i}")
        if not os.path.exists(chunk_file):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing chunk {i} for this upload."
            )
            
    # Final destination path
    _, ext = os.path.splitext(filename)
    final_filename = f"{upload_id}{ext}"
    final_path = os.path.join(MEETINGS_DIR, final_filename)
    
    # Merge all chunks into the final file
    with open(final_path, "wb") as final_file:
        for i in range(total_chunks):
            chunk_file = os.path.join(chunk_dir, f"chunk_{i}")
            with open(chunk_file, "rb") as chunk:
                shutil.copyfileobj(chunk, final_file)
                
    # Clean up the temporary chunk files
    shutil.rmtree(chunk_dir)
    
    # Create the Meeting database entry
    db_meeting = Meeting(
        title=title,
        file_path=final_path,
        status="pending"
    )
    db.add(db_meeting)
    await db.commit()
    await db.refresh(db_meeting)
    
    # Trigger Celery background task asynchronously!
    analyze_meeting_task.delay(db_meeting.id)
    
    # Return structured response
    meeting_out = MeetingOut.model_validate(db_meeting)
    return {
        "status": "success",
        "message": "File upload completed and merged successfully.",
        "meeting": meeting_out
    }
