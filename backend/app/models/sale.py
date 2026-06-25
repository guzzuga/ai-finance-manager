"""Sale model — penjualan produk di marketplace."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    marketplace_id = Column(String, ForeignKey("marketplaces.id"), nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    quantity = Column(Integer, nullable=False, default=1)
    price_per_unit = Column(Integer, nullable=False)  # Harga jual per pcs
    total_revenue = Column(Integer, nullable=False)  # quantity * price_per_unit
    hpp_per_unit = Column(Integer, nullable=False, default=0)  # HPP per pcs
    total_hpp = Column(Integer, nullable=False, default=0)  # quantity * hpp_per_unit
    marketplace_fee = Column(Integer, nullable=False, default=0)  # Fee marketplace
    shipping_cost = Column(Integer, nullable=False, default=0)  # Ongkir seller
    discount = Column(Integer, nullable=False, default=0)  # Diskon/voucher
    net_revenue = Column(Integer, nullable=False, default=0)  # Revenue - fee - ongkir - diskon
    profit = Column(Integer, nullable=False, default=0)  # net_revenue - total_hpp
    order_id = Column(String, nullable=True)  # No order marketplace
    status = Column(String, nullable=False, default="completed")  # completed, returned, cancelled
    settled = Column(Boolean, default=False)  # Sudah cair?
    settlement_date = Column(String, nullable=True)  # Tanggal pencairan
    notes = Column(String, nullable=True)
    raw_message = Column(String, nullable=True)
    source = Column(String, default="telegram")  # telegram, web, import
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", foreign_keys=[product_id])
    marketplace = relationship("Marketplace", foreign_keys=[marketplace_id])
