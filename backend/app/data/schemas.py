from __future__ import annotations

from pydantic import BaseModel, Field


class NormalizedTower(BaseModel):
    radio: str
    mcc: int
    mnc: int
    area_code: int
    cell_id: int
    lon: float = Field(ge=-180.0, le=180.0)
    lat: float = Field(ge=-90.0, le=90.0)
    range_m: float = Field(ge=0.0)
    samples: int = Field(ge=0)
    updated_ts: str
    operator_label: str


class CorridorSegmentRecord(BaseModel):
    segment_id: str
    route_id: str
    sequence: int
    start_lon: float
    start_lat: float
    end_lon: float
    end_lat: float
    length_m: int
    jio_estimated_score: float = Field(ge=0.0, le=100.0)
    airtel_estimated_score: float = Field(ge=0.0, le=100.0)
