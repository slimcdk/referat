from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Float, ForeignKey, Text, Integer
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class MeetingChunk(Base):
    __tablename__ = "meeting_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    clip_id: Mapped[int] = mapped_column(ForeignKey("meeting_clips.id", ondelete="CASCADE"), nullable=True) # Now supports granular mapping to clips
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(384), nullable=True)
