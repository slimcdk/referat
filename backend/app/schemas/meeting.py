from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class MeetingBase(BaseModel):
    title: str

class MeetingCreate(BaseModel):
    title: str

class ClipOut(BaseModel):
    id: int
    meeting_id: int
    title: str
    file_path: str
    sequence_number: int
    status: str
    duration: Optional[float] = None
    transcript_raw: Optional[str] = None
    transcript_clean: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class MeetingOut(MeetingBase):
    id: int
    title: str
    date: datetime
    status: str
    file_path: Optional[str] = None # Left for backward compatibility, but clips should be used
    transcript_raw: Optional[str] = None
    transcript_clean: Optional[str] = None
    summary: Optional[str] = None
    clips: List[ClipOut] = []

    class Config:
        from_attributes = True

class ChunkUploadResponse(BaseModel):
    status: str
    message: str
    chunk_index: int

class CompleteUploadResponse(BaseModel):
    status: str
    message: str
    clip: ClipOut
