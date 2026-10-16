import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.observability.metrics import INCIDENT_RECOVERY
from app.observability.models import AlertIncident

logger = logging.getLogger(__name__)
router = APIRouter(tags=["observability-internal"])


@router.post("/internal/alertmanager", status_code=status.HTTP_202_ACCEPTED)
async def receive_alertmanager_event(
    payload: dict[str, object],
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    alerts = payload.get("alerts", [])
    if not isinstance(alerts, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Campo alerts inválido",
        )

    processed = 0
    for item in alerts:
        if not isinstance(item, dict):
            continue
        labels = item.get("labels", {})
        fingerprint = item.get("fingerprint")
        if not isinstance(labels, dict) or not isinstance(fingerprint, str):
            continue
        alert_name = str(labels.get("alertname", "unknown"))[:128]
        starts_at = _parse_datetime(item.get("startsAt"))
        status_value = item.get("status")
        incident = await session.get(AlertIncident, fingerprint)
        if status_value == "firing" and incident is None:
            session.add(
                AlertIncident(
                    fingerprint=fingerprint,
                    alert_name=alert_name,
                    started_at=starts_at,
                )
            )
            logger.warning("alert_fired", extra={"alert_name": alert_name})
            processed += 1
        elif (
            status_value == "resolved"
            and incident is not None
            and incident.ended_at is None
        ):
            ended_at = _parse_datetime(item.get("endsAt"))
            incident.ended_at = ended_at
            started_at = incident.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            duration = max((ended_at - started_at).total_seconds(), 0)
            INCIDENT_RECOVERY.labels(alert_name=incident.alert_name).observe(duration)
            logger.warning(
                "alert_resolved",
                extra={"alert_name": alert_name, "recovery_seconds": duration},
            )
            processed += 1
    await session.commit()
    return {"processed": processed}


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

