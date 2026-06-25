"""Production model — catatan produksi konveksi."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Production(Base):
    __tablename__ = "productions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    quantity = Column(Integer, nullable=False)  # Jumlah produksi
    cost_per_unit = Column(Integer, nullable=False, default=0)  # Biaya per pcs (bahan + upah)
    total_cost = Column(Integer, nullable=False, default=0)  # quantity * cost_per_unit
    notes = Column(String, nullable=True)  # e.g. "10 meter kain, upah jahit 15rb/pcs"
    raw_message = Column(String, nullable=True)
    source = Column(String, default="telegram")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    product = relationship("Product", foreign_keys=[product_id])
