from uuid import UUID

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException
from rq import Queue
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import Flight
from app.schemas.schemas import ProcessResult, StatusResult

router = APIRouter(prefix="/flights", tags=["tasks"], dependencies=[Depends(get_current_user)])

_CONFLICT = {"odm_queued", "odm_processing"}


@router.post("/{flight_id}/process", response_model=ProcessResult)
def process_flight(flight_id: UUID, db: Session = Depends(get_db)):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not found")
    if flight.status in _CONFLICT:
        raise HTTPException(409, f"Cannot re-process: flight is already in status '{flight.status}'")

    conn = redis.from_url(settings.redis_url)
    job = Queue(connection=conn).enqueue(
        "tasks.odm_task.run_odm_pipeline", str(flight_id), job_timeout=14400
    )
    flight.status = "odm_queued"
    flight.rq_job_id = job.id
    db.commit()
    return ProcessResult(job_id=job.id, status="odm_queued")


@router.post("/{flight_id}/recalculate-indices", response_model=ProcessResult)
def recalculate_indices(flight_id: UUID, db: Session = Depends(get_db)):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not found")
    if flight.status not in ("indices_done", "odm_done"):
        raise HTTPException(409, f"Recalculate requires status 'indices_done' or 'odm_done', got '{flight.status}'")

    conn = redis.from_url(settings.redis_url)
    job = Queue(connection=conn).enqueue(
        "tasks.indices_task.run_indices_pipeline", str(flight_id), job_timeout=3600
    )
    return ProcessResult(job_id=job.id, status="recalculating")


@router.post("/{flight_id}/recalculate-anomalies", response_model=ProcessResult)
def recalculate_anomalies(flight_id: UUID, db: Session = Depends(get_db)):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not found")
    if flight.status != "indices_done":
        raise HTTPException(409, f"Recalculate requires status 'indices_done', got '{flight.status}'")

    conn = redis.from_url(settings.redis_url)
    job = Queue(connection=conn).enqueue(
        "tasks.segmentation_task.run_segmentation", str(flight_id), job_timeout=3600
    )
    return ProcessResult(job_id=job.id, status="recalculating")


@router.get("/{flight_id}/status", response_model=StatusResult)
def get_status(flight_id: UUID, db: Session = Depends(get_db)):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not found")
    odm_progress: int | None = None
    if flight.status == "odm_processing" and flight.odm_task_uuid:
        try:
            r = httpx.get(f"{settings.nodeodm_url}/task/{flight.odm_task_uuid}/info", timeout=5.0)
            if r.status_code == 200:
                odm_progress = int(r.json().get("progress", 0))
        except Exception:
            pass
    return StatusResult(
        flight_id=flight.id,
        status=flight.status,
        odm_progress=odm_progress,
        job_id=flight.rq_job_id,
    )
