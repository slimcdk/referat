from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from app.core.database import Base

class Speaker(Base):
    __tablename__ = "speakers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    voiceprint_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    assigned_name: Mapped[str] = mapped_column(String(255), nullable=False)
