"""Category model."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime
from app.database.connection import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'pemasukan' or 'pengeluaran'
    icon = Column(String, nullable=True)
    keywords = Column(String, nullable=True)  # JSON string
    user_id = Column(String, nullable=True)  # NULL = global default
    created_at = Column(DateTime, default=datetime.utcnow)
