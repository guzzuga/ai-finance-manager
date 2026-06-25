"""Material model — bahan baku konveksi."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean
from app.database.connection import Base


class Material(Base):
    __tablename__ = "materials"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)  # e.g. "Kain Katun"
    unit = Column(String, nullable=False, default="meter")  # meter, roll, kg, yard
    stock = Column(Float, nullable=False, default=0)  # Stok saat ini
    price_per_unit = Column(Integer, nullable=False, default=0)  # Harga per unit
    min_stock = Column(Float, nullable=True, default=0)  # Minimum stok (alert)
    supplier = Column(String, nullable=True)  # Nama supplier
    notes = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
