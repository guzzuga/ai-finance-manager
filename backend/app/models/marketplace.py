"""Marketplace model — platform penjualan."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean
from app.database.connection import Base


class Marketplace(Base):
    __tablename__ = "marketplaces"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)  # e.g. "Shopee", "Tokopedia"
    fee_percent = Column(Float, nullable=False, default=0)  # Fee % (e.g. 5.0 = 5%)
    fee_fixed = Column(Integer, nullable=False, default=0)  # Fee tetap per transaksi
    icon = Column(String, nullable=True)  # Emoji/icon
    settlement_days = Column(Integer, nullable=True, default=3)  # Hari pencairan dana
    notes = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
