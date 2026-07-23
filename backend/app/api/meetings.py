import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.meeting import Meeting
from app.models.meeting_clip import MeetingClip
from app.models.meeting_chunk import MeetingChunk
from app.schemas.meeting import ChunkUploadResponse, CompleteUploadResponse, MeetingOut, MeetingCreate, ClipOut

router = APIRouter(prefix="/meetings", tags=["meetings"])

# Storage directory setups
TEMP_DIR = os.path.join(settings.LOCAL_STORAGE_DIR, "temp")
MEETINGS_DIR = os.path.join(settings.LOCAL_STORAGE_DIR, "meetings")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(MEETINGS_DIR, exist_ok=True)

# 1. Create empty meeting
@router.post("", response_model=MeetingOut)
async def create_meeting(
    meeting_in: MeetingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_meeting = Meeting(
        title=meeting_in.title,
        status="empty"
    )
    db.add(db_meeting)
    await db.commit()
    await db.refresh(db_meeting)
    return db_meeting

# 2. List all meetings (with their clips)
@router.get("", response_model=List[MeetingOut])
async def list_meetings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Meeting).options(selectinload(Meeting.clips)).order_by(Meeting.date.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

# 3. Retrieve single meeting details
@router.get("/{meeting_id}", response_model=MeetingOut)
async def get_meeting(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Meeting).options(selectinload(Meeting.clips)).filter(Meeting.id == meeting_id)
    result = await db.execute(stmt)
    meeting = result.scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting

# 4. Delete meeting and all clips
@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Meeting).options(selectinload(Meeting.clips)).filter(Meeting.id == meeting_id)
    result = await db.execute(stmt)
    meeting = result.scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    # Delete clip files on disk
    for clip in meeting.clips:
        if clip.file_path and os.path.exists(clip.file_path):
            try:
                os.remove(clip.file_path)
                # Also delete associated output folders if they exist
                clip_id_str = os.path.basename(clip.file_path).split('.')[0]
                clip_outdir = os.path.join(settings.LOCAL_STORAGE_DIR, "pipeline", "output", clip_id_str)
                if os.path.exists(clip_outdir):
                    shutil.rmtree(clip_outdir)
            except Exception as e:
                print(f"Error deleting file/folder: {str(e)}")
                
    await db.delete(meeting)
    await db.commit()
    return {"status": "success", "message": "Meeting and associated clips deleted successfully."}

# 5. Upload chunk (independent of meeting structure)
@router.post("/upload/chunk", response_model=ChunkUploadResponse)
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    chunk_dir = os.path.join(TEMP_DIR, upload_id)
    os.makedirs(chunk_dir, exist_ok=True)
    
    chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index}")
    
    with open(chunk_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {
        "status": "success",
        "message": f"Chunk {chunk_index} uploaded successfully.",
        "chunk_index": chunk_index
    }

# 6. Finalize clip upload under a specific meeting
@router.post("/{meeting_id}/clips/upload/complete", response_model=CompleteUploadResponse)
async def complete_upload(
    meeting_id: int,
    upload_id: str = Form(...),
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
        
    for i in range(total_chunks):
        chunk_file = os.path.join(chunk_dir, f"chunk_{i}")
        if not os.path.exists(chunk_file):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing chunk {i} for this upload."
            )
            
    _, ext = os.path.splitext(filename)
    final_filename = f"{upload_id}{ext}"
    final_path = os.path.join(MEETINGS_DIR, final_filename)
    
    with open(final_path, "wb") as final_file:
        for i in range(total_chunks):
            chunk_file = os.path.join(chunk_dir, f"chunk_{i}")
            with open(chunk_file, "rb") as chunk:
                shutil.copyfileobj(chunk, final_file)
                
    shutil.rmtree(chunk_dir)
    
    # Retrieve the meeting to verify it exists and determine sequence number
    stmt = select(Meeting).options(selectinload(Meeting.clips)).filter(Meeting.id == meeting_id)
    result = await db.execute(stmt)
    meeting = result.scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    sequence_num = len(meeting.clips) + 1
    
    # Create the MeetingClip entry in the database
    db_clip = MeetingClip(
        meeting_id=meeting_id,
        title=filename,
        file_path=final_path,
        sequence_number=sequence_num,
        status="pending"
    )
    db.add(db_clip)
    
    # If the meeting was empty, update its status to indicate it now has clips
    if meeting.status == "empty":
        meeting.status = "pending"
        
    await db.commit()
    await db.refresh(db_clip)
    
    clip_out = ClipOut.model_validate(db_clip)
    return {
        "status": "success",
        "message": "Clip upload completed and merged successfully under the meeting.",
        "clip": clip_out
    }

# 7. Trigger single clip processing
@router.post("/clips/{clip_id}/process")
async def process_clip(
    clip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.tasks.meeting_pipeline import analyze_clip_task
    
    stmt = select(MeetingClip).filter(MeetingClip.id == clip_id)
    result = await db.execute(stmt)
    clip = result.scalars().first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
        
    clip.status = "processing"
    await db.commit()
    
    analyze_clip_task.delay(clip_id)
    return {"status": "success", "message": "Clip processing started asynchronously."}

# 8. Trigger overall meeting summary aggregation
@router.post("/{meeting_id}/aggregate")
async def aggregate_meeting(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.tasks.meeting_pipeline import aggregate_meeting_task
    
    stmt = select(Meeting).filter(Meeting.id == meeting_id)
    result = await db.execute(stmt)
    meeting = result.scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    meeting.status = "processing"
    await db.commit()
    
    aggregate_meeting_task.delay(meeting_id)
    return {"status": "success", "message": "Meeting summary aggregation started asynchronously."}

# 9. List all clips (both assigned and unassigned)
@router.get("/clips/all", response_model=List[ClipOut])
async def list_all_clips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(MeetingClip).order_by(MeetingClip.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

# 10. Finalize a standalone clip upload (no meeting_id required)
@router.post("/clips/upload/complete", response_model=CompleteUploadResponse)
async def complete_standalone_upload(
    upload_id: str = Form(...),
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
        
    for i in range(total_chunks):
        chunk_file = os.path.join(chunk_dir, f"chunk_{i}")
        if not os.path.exists(chunk_file):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing chunk {i} for this upload."
            )
            
    _, ext = os.path.splitext(filename)
    final_filename = f"{upload_id}{ext}"
    final_path = os.path.join(MEETINGS_DIR, final_filename)
    
    with open(final_path, "wb") as final_file:
        for i in range(total_chunks):
            chunk_file = os.path.join(chunk_dir, f"chunk_{i}")
            with open(chunk_file, "rb") as chunk:
                shutil.copyfileobj(chunk, final_file)
                
    shutil.rmtree(chunk_dir)
    
    # Create the standalone MeetingClip entry (meeting_id = None)
    db_clip = MeetingClip(
        meeting_id=None,
        title=filename,
        file_path=final_path,
        sequence_number=1,
        status="pending"
    )
    db.add(db_clip)
    await db.commit()
    await db.refresh(db_clip)
    
    clip_out = ClipOut.model_validate(db_clip)
    return {
        "status": "success",
        "message": "Standalone clip upload completed and merged successfully.",
        "clip": clip_out
    }

# 11. Assign a clip to an existing referat
@router.patch("/clips/{clip_id}")
async def assign_clip(
    clip_id: int,
    meeting_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(MeetingClip).filter(MeetingClip.id == clip_id)
    result = await db.execute(stmt)
    clip = result.scalars().first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
        
    stmt_m = select(Meeting).options(selectinload(Meeting.clips)).filter(Meeting.id == meeting_id)
    result_m = await db.execute(stmt_m)
    meeting = result_m.scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Target referat not found")
        
    # Update clip details
    seq_num = len(meeting.clips) + 1
    clip.meeting_id = meeting_id
    clip.sequence_number = seq_num
    
    # Also update associated search chunks to point to this meeting
    await db.execute(
        MeetingChunk.__table__.update()
        .where(MeetingChunk.clip_id == clip_id)
        .values(meeting_id=meeting_id)
    )
    
    if meeting.status == "empty":
        meeting.status = "pending"
        
    await db.commit()
    await db.refresh(clip)
    return {
        "status": "success",
        "message": "Clip successfully assigned to the referat.",
        "clip": ClipOut.model_validate(clip)
    }

# 12. Delete a single standalone clip
@router.delete("/clips/{clip_id}")
async def delete_standalone_clip(
    clip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(MeetingClip).filter(MeetingClip.id == clip_id)
    result = await db.execute(stmt)
    clip = result.scalars().first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
        
    # Delete clip file on disk
    if clip.file_path and os.path.exists(clip.file_path):
        try:
            os.remove(clip.file_path)
            clip_id_str = os.path.basename(clip.file_path).split('.')[0]
            clip_outdir = os.path.join(settings.LOCAL_STORAGE_DIR, "pipeline", "output", clip_id_str)
            if os.path.exists(clip_outdir):
                shutil.rmtree(clip_outdir)
        except Exception as e:
            print(f"Error deleting file/folder: {str(e)}")
            
    await db.delete(clip)
    await db.commit()
    return {"status": "success", "message": "Clip deleted successfully."}
