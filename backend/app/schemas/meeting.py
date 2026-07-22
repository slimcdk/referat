from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MeetingBase(BaseModel):
    title: str

class MeetingCreate(MeetingBase):
    file_path: str

class MeetingOut(MeetingBase):
    id: int
    title: str
    date: datetime
    file_path: str
    status: str
    transcript_raw: Optional[str] = None
    transcript_clean: Optional[str] = None
    summary: Optional[str] = None

    class Config:
        from_attributes = True

class ChunkUploadResponse(BaseModel):
    status: str
    message: str
    chunk_index: int

class CompleteUploadResponse(BaseModel):
    status: str
    message: str
    meeting: MeetingOut
