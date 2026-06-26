"""Product Category model — kategori produk konveksi."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime
from app.database.connection import Base


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)  # e.g. "Seragam SD"
    icon = Column(String, nullable=True, default="📦")  # emoji
    created_at = Column(DateTime, default=datetime.utcnow)
