from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import mapping, shape
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import AnomalyZone, Field, FieldMarker, Flight, IndexMap
from app.schemas.schemas import FieldCreate, FieldMarkerCreate, FieldMarkerOut, FieldOut, NdviHistoryPoint

router = APIRouter(prefix="/fields", tags=["fields"], dependencies=[Depends(get_current_user)])


def _serialize(field: Field) -> FieldOut:
    boundary = None
    if field.boundary is not None:
        boundary = dict(mapping(to_shape(field.boundary)))
    return FieldOut(
        id=field.id,
        name=field.name,
        area_ha=field.area_ha,
        created_at=field.created_at,
        boundary=boundary,
    )


@router.post("", response_model=FieldOut, status_code=201, dependencies=[Depends(require_admin)])
def create_field(data: FieldCreate, db: Session = Depends(get_db)):
    boundary = from_shape(shape(data.boundary), srid=4326) if data.boundary else None
    field = Field(name=data.name, boundary=boundary, area_ha=data.area_ha)
    db.add(field)
    db.commit()
    db.refresh(field)
    return _serialize(field)


@router.get("", response_model=list[FieldOut])
def list_fields(db: Session = Depends(get_db)):
    return [_serialize(f) for f in db.query(Field).all()]


@router.get("/{field_id}", response_model=FieldOut)
def get_field(field_id: UUID, db: Session = Depends(get_db)):
    field = db.get(Field, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    return _serialize(field)


@router.delete("/{field_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_field(field_id: UUID, db: Session = Depends(get_db)):
    field = db.get(Field, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    db.delete(field)
    db.commit()


@router.get("/{field_id}/ndvi-history", response_model=list[NdviHistoryPoint])
def ndvi_history(field_id: UUID, db: Session = Depends(get_db)):
    flights = (
        db.query(Flight)
        .filter(Flight.field_id == field_id, Flight.status == "indices_done")
        .order_by(Flight.flown_at)
        .all()
    )
    result = []
    for fl in flights:
        ndvi_map = next((im for im in fl.index_maps if im.index_type == "NDVI"), None)
        evi_map = next((im for im in fl.index_maps if im.index_type == "EVI"), None)
        anomaly = db.query(AnomalyZone).filter(
            AnomalyZone.flight_id == fl.id, AnomalyZone.index_type == "NDVI"
        ).first()
        result.append(NdviHistoryPoint(
            flight_id=fl.id,
            flown_at=fl.flown_at,
            ndvi_mean=ndvi_map.mean_value if ndvi_map else None,
            evi_mean=evi_map.mean_value if evi_map else None,
            anomaly_ha=anomaly.area_ha if anomaly else 0.0,
        ))
    return result


@router.get("/{field_id}/markers", response_model=list[FieldMarkerOut])
def list_markers(field_id: UUID, db: Session = Depends(get_db)):
    return db.query(FieldMarker).filter(FieldMarker.field_id == field_id).all()


@router.post("/{field_id}/markers", response_model=FieldMarkerOut, status_code=201)
def create_marker(field_id: UUID, data: FieldMarkerCreate, db: Session = Depends(get_db)):
    field = db.get(Field, field_id)
    if not field:
        raise HTTPException(404, "Field not found")
    marker = FieldMarker(field_id=field_id, lat=data.lat, lon=data.lon, note=data.note)
    db.add(marker)
    db.commit()
    db.refresh(marker)
    return marker


@router.delete("/{field_id}/markers/{marker_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_marker(field_id: UUID, marker_id: UUID, db: Session = Depends(get_db)):
    marker = db.query(FieldMarker).filter(
        FieldMarker.id == marker_id, FieldMarker.field_id == field_id
    ).first()
    if not marker:
        raise HTTPException(404, "Marker not found")
    db.delete(marker)
    db.commit()
