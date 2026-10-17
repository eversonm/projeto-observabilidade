from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.products.models import Base


class AlertIncident(Base):
    __tablename__ = "alert_incidents"

    fingerprint: Mapped[str] = mapped_column(String(128), primary_key=True)
    alert_name: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
