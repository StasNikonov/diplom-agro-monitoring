from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FieldCreate(BaseModel):
    name: str
    boundary: dict[str, Any] | None = None
    area_ha: float | None = None


class FieldOut(BaseModel):
    id: UUID
    name: str
    area_ha: float | None = None
    created_at: datetime
    boundary: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class FlightCreate(BaseModel):
    field_id: UUID
    flown_at: datetime


class IndexMapOut(BaseModel):
    id: UUID
    index_type: str
    file_path: str
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FlightOut(BaseModel):
    id: UUID
    field_id: UUID | None = None
    flown_at: datetime
    raw_path: str | None = None
    status: str
    notes: str | None = None
    created_at: datetime
    index_maps: list[IndexMapOut] = []
    has_dsm: bool = False

    model_config = ConfigDict(from_attributes=True)


class IndexRecommendation(BaseModel):
    index_type: str
    category: str
    color: str
    recommendation: str
    is_proxy: bool = False


class FlightPatch(BaseModel):
    notes: str


class FieldMarkerCreate(BaseModel):
    lat: float
    lon: float
    note: str = ""


class FieldMarkerOut(BaseModel):
    id: UUID
    field_id: UUID
    lat: float
    lon: float
    note: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NdviHistoryPoint(BaseModel):
    flight_id: UUID
    flown_at: datetime
    ndvi_mean: float | None
    evi_mean: float | None
    anomaly_ha: float | None


class FlightShort(BaseModel):
    id: UUID
    field_id: UUID | None = None
    flown_at: datetime
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadResult(BaseModel):
    uploaded: int
    size_mb: float


class ProcessResult(BaseModel):
    job_id: str
    status: str


class StatusResult(BaseModel):
    flight_id: UUID
    status: str
    odm_progress: int | None = None
    job_id: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str
    role: str


class UserCreate(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: UUID
    username: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
