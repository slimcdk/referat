from pydantic import BaseModel
from typing import List, Optional

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10

class SearchResult(BaseModel):
    meeting_id: int
    meeting_title: str
    start_time: float
    end_time: float
    text: str
    similarity: float

class SystemSettingsSchema(BaseModel):
    llm_size: str
    data_retention_days: int

    class Config:
        from_attributes = True
