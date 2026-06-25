"""User model."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime
from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=True)  # bcrypt hashed
    platform = Column(String, nullable=False, default="web")
    platform_id = Column(String, nullable=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
