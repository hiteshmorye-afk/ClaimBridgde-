from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    full_name = Column(
        String(150),
        nullable=False,
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
    )

    role = Column(
        String(50),
        nullable=False,
    )

    password_hash = Column(
        String(255),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )