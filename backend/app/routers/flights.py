from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.config import settings
from app.database import get_db
from app.models import Flight
from app.schemas.schemas import FlightCreate, FlightOut, FlightPatch, UploadResult
from app.services.storage import ensure_flight_dirs

router = APIRouter(prefix="/flights", tags=["flights"], dependencies=[Depends(get_current_user)])

_ALLOWED = {".jpg", ".jpeg", ".tif", ".tiff"}


def _out(flight: Flight) -> FlightOut:
    dsm_preview = Path(settings.data_dir) / "flights" / str(flight.id) / "results" / "dsm_preview.png"
    return FlightOut(
        id=flight.id,
        field_id=flight.field_id,
        flown_at=flight.flown_at,
        raw_path=flight.raw_path,
        status=flight.status,
        notes=flight.notes,
        created_at=flight.created_at,
        index_maps=list(flight.index_maps),
        has_dsm=dsm_preview.exists(),
    )


@router.post("", response_model=FlightOut, status_code=201)
def create_flight(data: FlightCreate, db: Session = Depends(get_db)):
    flight = Flight(field_id=data.field_id, flown_at=data.flown_at, status="uploaded")
    db.add(flight)
    db.flush()
    raw_dir, _ = ensure_flight_dirs(str(flight.id), settings.data_dir)
    flight.raw_path = str(raw_dir)
    db.commit()
    db.refresh(flight)
    return _out(flight)


@router.get("", response_model=list[FlightOut])
def list_flights(
    field_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Flight)
    if field_id:
        q = q.filter(Flight.field_id == field_id)
    if status:
        q = q.filter(Flight.status == status)
    return [_out(f) for f in q.all()]


@router.get("/{flight_id}", response_model=FlightOut)
def get_flight(flight_id: UUID, db: Session = Depends(get_db)):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not found")
    return _out(flight)


@router.patch("/{flight_id}/notes", response_model=FlightOut)
def update_notes(flight_id: UUID, data: FlightPatch, db: Session = Depends(get_db)):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not found")
    flight.notes = data.notes
    db.commit()
    db.refresh(flight)
    return _out(flight)


@router.delete("/{flight_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_flight(flight_id: UUID, db: Session = Depends(get_db)):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not found")
    db.delete(flight)
    db.commit()


@router.post("/{flight_id}/upload", response_model=UploadResult)
async def upload_images(
    flight_id: UUID,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not found")
    valid = [f for f in files if Path(f.filename or "").suffix.lower() in _ALLOWED]
    if len(valid) < 3:
        raise HTTPException(
            400,
            f"At least 3 valid image files required (.jpg/.jpeg/.tif/.tiff), got {len(valid)}",
        )
    raw_dir = Path(settings.data_dir) / "flights" / str(flight_id) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for up in valid:
        content = await up.read()
        (raw_dir / (up.filename or f"img_{total}.jpg")).write_bytes(content)
        total += len(content)
    return UploadResult(uploaded=len(valid), size_mb=round(total / 1024 / 1024, 2))
