from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Float, ForeignKey
from app.core.database import Base

class JobMetrics(Base):
    __tablename__ = "job_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), unique=True, nullable=False)
    video_length: Mapped[float] = mapped_column(Float, nullable=False)
    transcription_time: Mapped[float] = mapped_column(Float, nullable=True)
    ocr_time: Mapped[float] = mapped_column(Float, nullable=True)
    summarization_time: Mapped[float] = mapped_column(Float, nullable=True)
    total_processing_time: Mapped[float] = mapped_column(Float, nullable=False)
