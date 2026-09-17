import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_owner, require_writable_business
from app.errors import api_error
from app.models.business import Business
from app.models.location import Location
from app.models.user import User
from app.schemas.location import LocationCreate, LocationResponse, LocationUpdate
from app.services.shifts import active_locations

router = APIRouter(prefix="/locations", tags=["locations"])


def _get_location(db: Session, business_id: uuid.UUID, location_id: uuid.UUID) -> Location:
    location = db.execute(
        select(Location).where(
            Location.id == location_id,
            Location.business_id == business_id,
            Location.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if location is None:
        raise api_error(404, "location_not_found", "That shop zone doesn't exist.")
    return location


@router.get("", response_model=list[LocationResponse])
def list_locations(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[LocationResponse]:
    """Everyone in the business can read the zones: staff need them to see where they can start."""
    locations = active_locations(db, current_user.business_id)
    return [LocationResponse.model_validate(location) for location in locations]


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreate,
    current_user: User = Depends(require_owner),
    _: Business = Depends(require_writable_business),
    db: Session = Depends(get_db),
) -> LocationResponse:
    location = Location(
        business_id=current_user.business_id,
        name=payload.name.strip(),
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_m=payload.radius_m,
    )
    db.add(location)
    db.flush()
    db.refresh(location)
    return LocationResponse.model_validate(location)


@router.patch("/{location_id}", response_model=LocationResponse)
def update_location(
    location_id: uuid.UUID,
    payload: LocationUpdate,
    current_user: User = Depends(require_owner),
    _: Business = Depends(require_writable_business),
    db: Session = Depends(get_db),
) -> LocationResponse:
    location = _get_location(db, current_user.business_id, location_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(location, field, value)
    db.flush()
    db.refresh(location)
    return LocationResponse.model_validate(location)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(
    location_id: uuid.UUID,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> None:
    """Deactivated rather than deleted, so shifts recorded at this zone keep their history."""
    location = _get_location(db, current_user.business_id, location_id)
    location.is_active = False
