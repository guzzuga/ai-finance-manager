"""Transaction model."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from app.database.connection import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'pemasukan' or 'pengeluaran'
    category_id = Column(String, ForeignKey("categories.id"), nullable=True)
    amount = Column(Integer, nullable=False)
    note = Column(String, nullable=True)
    source = Column(String, default="web")  # 'web', 'telegram', 'import'
    raw_message = Column(String, nullable=True)
    quantity = Column(Float, nullable=True)  # e.g. 5.0
    unit = Column(String, nullable=True)  # e.g. 'pcs', 'meter', 'roll'
    price_per_unit = Column(Integer, nullable=True)  # calculated: amount / quantity
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
