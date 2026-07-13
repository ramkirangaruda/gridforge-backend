import logging

from sqlalchemy.exc import IntegrityError

from backend.core.auth import hash_password, verify_password
from backend.db.database import SessionLocal
from backend.db.models import UserORM

logger = logging.getLogger(__name__)


def create_user(username: str, password: str) -> None:
    user = UserORM(username=username, hashed_password=hash_password(password))
    with SessionLocal() as session:
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            logger.warning(f"Registration attempted for existing username: {username}")
            raise ValueError("Username already exists.")
    logger.info(f"Registered new user: {username}")


def authenticate_user(username: str, password: str) -> bool:
    with SessionLocal() as session:
        user = session.query(UserORM).filter(UserORM.username == username).first()
        if not user or not verify_password(password, user.hashed_password):
            return False
        return True
