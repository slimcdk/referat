from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer
from app.core.database import Base

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    llm_size: Mapped[str] = mapped_column(String(50), default="small", nullable=False)
    data_retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
