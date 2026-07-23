from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Text, ForeignKey, Integer, Float
from datetime import datetime, timezone
from app.core.database import Base

class MeetingClip(Base):
    __tablename__ = "meeting_clips"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True) # Now nullable/optional for standalone clips
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=True)
    transcript_raw: Mapped[str] = mapped_column(Text, nullable=True)
    transcript_clean: Mapped[str] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationship back to Meeting
    meeting = relationship("Meeting", back_populates="clips")
