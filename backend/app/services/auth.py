import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserStatus
from app.services.security import verify_password


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == normalize_email(email))).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: uuid.UUID | str) -> User | None:
    return db.get(User, user_id)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None or user.status != UserStatus.active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
