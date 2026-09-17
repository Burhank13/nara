import uuid

from pydantic import BaseModel, Field

from app.config import settings
from app.schemas.common import Name

Latitude = Field(ge=-90, le=90)
Longitude = Field(ge=-180, le=180)
Radius = Field(ge=settings.min_zone_radius_m, le=settings.max_zone_radius_m)


class LocationCreate(BaseModel):
    name: Name
    address: str | None = Field(default=None, max_length=500)
    latitude: float = Latitude
    longitude: float = Longitude
    radius_m: int = Field(
        default=settings.default_zone_radius_m, ge=settings.min_zone_radius_m, le=settings.max_zone_radius_m
    )


class LocationUpdate(BaseModel):
    name: Name | None = None
    address: str | None = Field(default=None, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_m: int | None = Field(default=None, ge=settings.min_zone_radius_m, le=settings.max_zone_radius_m)


class LocationResponse(BaseModel):
    id: uuid.UUID
    name: str
    address: str | None
    latitude: float
    longitude: float
    radius_m: int

    model_config = {"from_attributes": True}
