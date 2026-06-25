"""Product model — untuk produk konveksi."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean
from app.database.connection import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)  # e.g. "Kaos Polos L"
    sku = Column(String, nullable=True)  # e.g. "KPL-001"
    category = Column(String, nullable=True)  # e.g. "kaos", "kemeja", "celana"
    hpp = Column(Integer, nullable=False, default=0)  # Harga Pokok Produksi
    price = Column(Integer, nullable=False, default=0)  # Harga jual
    stock = Column(Integer, nullable=False, default=0)  # Stok saat ini
    unit = Column(String, nullable=False, default="pcs")  # pcs, lusin, dll
    min_stock = Column(Integer, nullable=True, default=0)  # Minimum stok (alert)
    notes = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    user_id = Column(String, nullable=True)  # NULL = global
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
