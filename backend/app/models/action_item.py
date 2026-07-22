from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey
from app.core.database import Base

class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    task: Mapped[str] = mapped_column(String(512), nullable=False)
    assignee: Mapped[str] = mapped_column(String(255), nullable=True)
    deadline: Mapped[str] = mapped_column(String(100), nullable=True)
