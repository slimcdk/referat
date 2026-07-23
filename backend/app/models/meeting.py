from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Text
from datetime import datetime, timezone
from app.core.database import Base
from typing import List

class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=True) # Now optional since files are under clips
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    transcript_raw: Mapped[str] = mapped_column(Text, nullable=True)
    transcript_clean: Mapped[str] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    clips = relationship("MeetingClip", back_populates="meeting", cascade="all, delete-orphan", lazy="selectin")
