"""Konveksi Service — CRUD & reports for products, materials, sales, production."""
import uuid
import re
import logging
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.material import Material
from app.models.marketplace import Marketplace
from app.models.sale import Sale
from app.models.production import Production
from app.models.transaction import Transaction
from app.services import google_sheets_service

logger = logging.getLogger(__name__)

# Product category auto-detection rules
_CATEGORY_RULES = [
    (r'almamater', 'Almamater'),
    (r'pramuka', 'Seragam Pramuka'),
    (r'batik', 'Seragam Batik'),
    (r'olah\s*raga|sport', 'Kaos Olahraga'),
    (r'kaos\s*polos|polos', 'Kaos Polos'),
    (r'kaos', 'Kaos'),
    (r'kemeja', 'Kemeja'),
    (r'jas\b', 'Jas'),
    (r'celana', 'Celana'),
    (r'wearpack|safety', 'Wearpack'),
    (r'topi', 'Topi'),
    (r'seragam\s*sd|sd\b', 'Seragam SD'),
    (r'seragam\s*smp|smp\b', 'Seragam SMP'),
    (r'seragam\s*sma|sma\b', 'Seragam SMA'),
    (r'kerja|kantor|korporat', 'Seragam Kerja'),
    (r'seragam\s*sekolah', 'Seragam SD'),
    (r'seragam', 'Seragam Kerja'),
]


def detect_product_category(name: str) -> str:
    """Auto-detect product category from name."""
    name_lower = name.lower()
    for pattern, category in _CATEGORY_RULES:
        if re.search(pattern, name_lower):
            return category
    return 'Lainnya'


class KonveksiService:
    """Service layer for konveksi operations."""

    # ==================== PRODUCTS ====================

    @staticmethod
    def create_product(db: Session, data: dict) -> Product:
        """Create a new product."""
        product = Product(
            id=str(uuid.uuid4()),
            name=data["name"],
            sku=data.get("sku"),
            category=data.get("category") or detect_product_category(data["name"]),
            hpp=data.get("hpp", 0),
            price=data.get("price", 0),
            stock=data.get("stock", 0),
            unit=data.get("unit", "pcs"),
            min_stock=data.get("min_stock", 0),
            notes=data.get("notes"),
            user_id=data.get("user_id"),
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def get_products(db: Session, user_id: str = None, active_only: bool = True) -> list:
        """Get all products."""
        query = db.query(Product)
        if active_only:
            query = query.filter(Product.active == True)
        if user_id:
            query = query.filter(Product.user_id == user_id)
        return query.order_by(Product.name).all()

    @staticmethod
    def get_product(db: Session, product_id: str) -> Optional[Product]:
        """Get a single product by ID."""
        return db.query(Product).filter(Product.id == product_id).first()

    @staticmethod
    def get_product_by_name(db: Session, name: str) -> Optional[Product]:
        """Find product by name (case-insensitive partial match)."""
        return db.query(Product).filter(
            Product.name.ilike(f"%{name}%"),
            Product.active == True,
        ).first()

    @staticmethod
    def update_product(db: Session, product_id: str, data: dict) -> Optional[Product]:
        """Update a product."""
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None
        for key, value in data.items():
            if hasattr(product, key) and key != "id":
                setattr(product, key, value)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def update_stock(db: Session, product_id: str, quantity_change: int) -> Optional[Product]:
        """Update product stock (positive = add, negative = subtract)."""
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None
        product.stock = max(0, product.stock + quantity_change)
        db.commit()
        db.refresh(product)
        return product

    # ==================== MATERIALS ====================

    @staticmethod
    def create_material(db: Session, data: dict) -> Material:
        """Create a new material."""
        material = Material(
            id=str(uuid.uuid4()),
            name=data["name"],
            unit=data.get("unit", "meter"),
            stock=data.get("stock", 0),
            price_per_unit=data.get("price_per_unit", 0),
            min_stock=data.get("min_stock", 0),
            supplier=data.get("supplier"),
            notes=data.get("notes"),
            user_id=data.get("user_id"),
        )
        db.add(material)
        db.commit()
        db.refresh(material)
        return material

    @staticmethod
    def get_materials(db: Session, user_id: str = None, active_only: bool = True) -> list:
        """Get all materials."""
        query = db.query(Material)
        if active_only:
            query = query.filter(Material.active == True)
        if user_id:
            query = query.filter(Material.user_id == user_id)
        return query.order_by(Material.name).all()

    @staticmethod
    def get_material(db: Session, material_id: str) -> Optional[Material]:
        """Get a single material."""
        return db.query(Material).filter(Material.id == material_id).first()

    @staticmethod
    def get_material_by_name(db: Session, name: str) -> Optional[Material]:
        """Find material by name."""
        return db.query(Material).filter(
            Material.name.ilike(f"%{name}%"),
            Material.active == True,
        ).first()

    @staticmethod
    def update_material_stock(db: Session, material_id: str, quantity_change: float) -> Optional[Material]:
        """Update material stock."""
        material = db.query(Material).filter(Material.id == material_id).first()
        if not material:
            return None
        material.stock = max(0, material.stock + quantity_change)
        db.commit()
        db.refresh(material)
        return material

    # ==================== MARKETPLACES ====================

    @staticmethod
    def create_marketplace(db: Session, data: dict) -> Marketplace:
        """Create a new marketplace."""
        marketplace = Marketplace(
            id=str(uuid.uuid4()),
            name=data["name"],
            fee_percent=data.get("fee_percent", 0),
            fee_fixed=data.get("fee_fixed", 0),
            icon=data.get("icon", "🛒"),
            settlement_days=data.get("settlement_days", 3),
            notes=data.get("notes"),
            user_id=data.get("user_id"),
        )
        db.add(marketplace)
        db.commit()
        db.refresh(marketplace)
        return marketplace

    @staticmethod
    def get_marketplaces(db: Session, active_only: bool = True) -> list:
        """Get all marketplaces."""
        query = db.query(Marketplace)
        if active_only:
            query = query.filter(Marketplace.active == True)
        return query.order_by(Marketplace.name).all()

    @staticmethod
    def get_marketplace(db: Session, marketplace_id: str) -> Optional[Marketplace]:
        """Get a single marketplace."""
        return db.query(Marketplace).filter(Marketplace.id == marketplace_id).first()

    @staticmethod
    def get_marketplace_by_name(db: Session, name: str) -> Optional[Marketplace]:
        """Find marketplace by name."""
        return db.query(Marketplace).filter(
            Marketplace.name.ilike(f"%{name}%"),
            Marketplace.active == True,
        ).first()

    # ==================== SALES ====================

    @staticmethod
    def create_sale(db: Session, data: dict) -> Sale:
        """Create a sale record and auto-calculate fees & profit."""
        quantity = data.get("quantity", 1)
        price_per_unit = data.get("price_per_unit", 0)
        hpp_per_unit = data.get("hpp_per_unit", 0)
        shipping_cost = data.get("shipping_cost", 0)
        discount = data.get("discount", 0)

        # Get marketplace fee
        marketplace = db.query(Marketplace).filter(
            Marketplace.id == data.get("marketplace_id")
        ).first()
        fee_percent = marketplace.fee_percent if marketplace else 0
        fee_fixed = marketplace.fee_fixed if marketplace else 0

        total_revenue = quantity * price_per_unit
        total_hpp = quantity * hpp_per_unit
        marketplace_fee = round(total_revenue * fee_percent / 100) + fee_fixed
        net_revenue = total_revenue - marketplace_fee - shipping_cost - discount
        profit = net_revenue - total_hpp

        # Calculate settlement date
        settlement_date = None
        settled = False
        if marketplace and marketplace.settlement_days is not None:
            from datetime import timedelta, datetime as dt
            try:
                sale_date = dt.fromisoformat(data["date"])
                if marketplace.settlement_days == 0:
                    # Cash/offline — settled immediately
                    settled = True
                    settlement_date = data["date"]
                else:
                    settlement_date = (sale_date + timedelta(days=marketplace.settlement_days)).isoformat()
            except (ValueError, TypeError):
                pass

        sale = Sale(
            id=str(uuid.uuid4()),
            user_id=data["user_id"],
            product_id=data["product_id"],
            marketplace_id=data["marketplace_id"],
            date=data["date"],
            quantity=quantity,
            price_per_unit=price_per_unit,
            total_revenue=total_revenue,
            hpp_per_unit=hpp_per_unit,
            total_hpp=total_hpp,
            marketplace_fee=marketplace_fee,
            shipping_cost=shipping_cost,
            discount=discount,
            net_revenue=net_revenue,
            profit=profit,
            order_id=data.get("order_id"),
            status=data.get("status", "completed"),
            settled=settled,
            settlement_date=settlement_date,
            notes=data.get("notes"),
            raw_message=data.get("raw_message"),
            source=data.get("source", "telegram"),
        )
        db.add(sale)

        # Auto-decrease product stock
        product = db.query(Product).filter(Product.id == data["product_id"]).first()
        if product:
            product.stock = max(0, product.stock - quantity)

        # Auto-create pemasukan transaction (so it shows in general finance)
        if net_revenue > 0:
            # Find appropriate category for konveksi sales
            from app.models.category import Category
            # Use penjualan_offline for Offline/Toko, penjualan_online for marketplaces
            mp_name_lower = (marketplace.name if marketplace else "").lower()
            if "offline" in mp_name_lower or "toko" in mp_name_lower:
                sale_cat_name = "penjualan_offline"
            else:
                sale_cat_name = "penjualan_online"
            sale_cat = db.query(Category).filter(
                Category.name == sale_cat_name, Category.type == "pemasukan"
            ).first()
            # Fallback: try the other category
            if not sale_cat:
                fallback_name = "penjualan_online" if sale_cat_name == "penjualan_offline" else "penjualan_offline"
                sale_cat = db.query(Category).filter(
                    Category.name == fallback_name, Category.type == "pemasukan"
                ).first()
            transaction = Transaction(
                id=str(uuid.uuid4()),
                user_id=data["user_id"],
                date=data["date"],
                type="pemasukan",
                category_id=sale_cat.id if sale_cat else None,
                amount=net_revenue,
                note=f"Penjualan {product.name if product else ''} × {quantity} di {marketplace.name if marketplace else ''}",
                source=data.get("source", "telegram"),
                raw_message=data.get("raw_message"),
                quantity=quantity,
                unit="pcs",
                price_per_unit=price_per_unit,
            )
            db.add(transaction)

        db.commit()
        db.refresh(sale)

        # Sync to Google Sheets
        try:
            # 1. Sync to Penjualan_Konveksi tab
            google_sheets_service.append_penjualan(
                tanggal=sale.date,
                produk=product.name if product else "",
                marketplace=marketplace.name if marketplace else "",
                qty=quantity,
                harga_per_unit=price_per_unit,
                revenue=total_revenue,
                hpp=total_hpp,
                fee=marketplace_fee,
                ongkir=shipping_cost,
                laba=profit,
                order_id=data.get("order_id", ""),
                status="completed",
                tgl_cair=settlement_date or "",
            )
            # 2. Also sync transaction to Pemasukan Sheet1
            if net_revenue > 0:
                cat_name = sale_cat.name if sale_cat else "penjualan_online"
                google_sheets_service.append_transaction(
                    tanggal=sale.date,
                    jenis="pemasukan",
                    kategori=cat_name,
                    nominal=net_revenue,
                    catatan=f"Penjualan {product.name if product else ''} x{quantity} di {marketplace.name if marketplace else ''}",
                    sumber=data.get("source", "telegram"),
                    quantity=quantity,
                    unit="pcs",
                    price_per_unit=price_per_unit,
                )
        except Exception as e:
            logger.warning("Failed to sync penjualan to Google Sheets: %s", e)

        return sale

    @staticmethod
    def get_sales(
        db: Session,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        marketplace_id: Optional[str] = None,
        product_id: Optional[str] = None,
        limit: int = 50,
    ) -> list:
        """Get sales with filters."""
        query = db.query(Sale).filter(Sale.user_id == user_id)
        if start_date:
            query = query.filter(Sale.date >= start_date)
        if end_date:
            query = query.filter(Sale.date <= end_date)
        if marketplace_id:
            query = query.filter(Sale.marketplace_id == marketplace_id)
        if product_id:
            query = query.filter(Sale.product_id == product_id)
        return query.order_by(Sale.date.desc()).limit(limit).all()

    # ==================== PRODUCTION ====================

    @staticmethod
    def create_production(db: Session, data: dict) -> Production:
        """Record a production run and auto-increase product stock."""
        quantity = data.get("quantity", 0)
        cost_per_unit = data.get("cost_per_unit", 0)
        total_cost = quantity * cost_per_unit

        production = Production(
            id=str(uuid.uuid4()),
            user_id=data["user_id"],
            product_id=data["product_id"],
            date=data["date"],
            quantity=quantity,
            cost_per_unit=cost_per_unit,
            total_cost=total_cost,
            notes=data.get("notes"),
            raw_message=data.get("raw_message"),
            source=data.get("source", "telegram"),
        )
        db.add(production)

        # Auto-increase product stock
        product = db.query(Product).filter(Product.id == data["product_id"]).first()
        if product:
            product.stock += quantity
            # Update HPP (weighted average)
            if product.stock > 0 and cost_per_unit > 0:
                old_hpp = product.hpp
                old_stock = product.stock - quantity
                new_hpp = round((old_hpp * old_stock + cost_per_unit * quantity) / product.stock)
                product.hpp = new_hpp

        # Auto-create pengeluaran transaction
        if total_cost > 0:
            from app.models.category import Category
            prod_cat = db.query(Category).filter(
                Category.name == "biaya_produksi", Category.type == "pengeluaran"
            ).first()
            transaction = Transaction(
                id=str(uuid.uuid4()),
                user_id=data["user_id"],
                date=data["date"],
                type="pengeluaran",
                category_id=prod_cat.id if prod_cat else None,
                amount=total_cost,
                note=f"Produksi {product.name if product else ''} x{quantity}",
                source=data.get("source", "telegram"),
                raw_message=data.get("raw_message"),
                quantity=quantity,
                unit="pcs",
                price_per_unit=cost_per_unit,
            )
            db.add(transaction)

        db.commit()
        db.refresh(production)

        # Sync to Google Sheets
        try:
            # 1. Sync to Produksi tab
            google_sheets_service.append_produksi(
                tanggal=production.date,
                produk=product.name if product else "",
                qty=quantity,
                biaya_per_unit=cost_per_unit,
                total_biaya=total_cost,
                catatan=data.get("notes", ""),
            )
            # 2. Also sync transaction to Pengeluaran Sheet1
            if total_cost > 0:
                google_sheets_service.append_transaction(
                    tanggal=production.date,
                    jenis="pengeluaran",
                    kategori="biaya_produksi",
                    nominal=total_cost,
                    catatan=f"Produksi {product.name if product else ''} x{quantity}",
                    sumber=data.get("source", "telegram"),
                    quantity=quantity,
                    unit="pcs",
                    price_per_unit=cost_per_unit,
                )
        except Exception as e:
            logger.warning("Failed to sync produksi to Google Sheets: %s", e)

        return production

    # ==================== REPORTS ====================

    @staticmethod
    def get_laporan_konveksi(db: Session, user_id: str, start_date: str, end_date: str) -> dict:
        """Get konveksi profit/loss report for a period."""
        # Sales summary
        sales_data = (
            db.query(
                func.sum(Sale.total_revenue).label("total_revenue"),
                func.sum(Sale.total_hpp).label("total_hpp"),
                func.sum(Sale.marketplace_fee).label("total_fee"),
                func.sum(Sale.shipping_cost).label("total_shipping"),
                func.sum(Sale.discount).label("total_discount"),
                func.sum(Sale.net_revenue).label("total_net_revenue"),
                func.sum(Sale.profit).label("total_profit"),
                func.sum(Sale.quantity).label("total_qty"),
                func.count(Sale.id).label("total_orders"),
            )
            .filter(
                Sale.user_id == user_id,
                Sale.date >= start_date,
                Sale.date <= end_date,
                Sale.status == "completed",
            )
            .first()
        )

        # Production summary
        production_data = (
            db.query(
                func.sum(Production.total_cost).label("total_production_cost"),
                func.sum(Production.quantity).label("total_produced"),
            )
            .filter(
                Production.user_id == user_id,
                Production.date >= start_date,
                Production.date <= end_date,
            )
            .first()
        )

        # Sales per marketplace
        marketplace_breakdown = (
            db.query(
                Marketplace.name,
                Marketplace.icon,
                func.sum(Sale.quantity).label("qty"),
                func.sum(Sale.total_revenue).label("revenue"),
                func.sum(Sale.profit).label("profit"),
                func.count(Sale.id).label("orders"),
            )
            .join(Marketplace, Sale.marketplace_id == Marketplace.id)
            .filter(
                Sale.user_id == user_id,
                Sale.date >= start_date,
                Sale.date <= end_date,
                Sale.status == "completed",
            )
            .group_by(Marketplace.name, Marketplace.icon)
            .order_by(func.sum(Sale.profit).desc())
            .all()
        )

        # Sales per product
        product_breakdown = (
            db.query(
                Product.name,
                func.sum(Sale.quantity).label("qty"),
                func.sum(Sale.total_revenue).label("revenue"),
                func.sum(Sale.profit).label("profit"),
                func.sum(Sale.marketplace_fee).label("fee"),
            )
            .join(Product, Sale.product_id == Product.id)
            .filter(
                Sale.user_id == user_id,
                Sale.date >= start_date,
                Sale.date <= end_date,
                Sale.status == "completed",
            )
            .group_by(Product.name)
            .order_by(func.sum(Sale.profit).desc())
            .all()
        )

        return {
            "total_revenue": sales_data.total_revenue or 0,
            "total_hpp": sales_data.total_hpp or 0,
            "total_fee": sales_data.total_fee or 0,
            "total_shipping": sales_data.total_shipping or 0,
            "total_discount": sales_data.total_discount or 0,
            "total_net_revenue": sales_data.total_net_revenue or 0,
            "total_profit": sales_data.total_profit or 0,
            "total_qty_sold": sales_data.total_qty or 0,
            "total_orders": sales_data.total_orders or 0,
            "total_production_cost": production_data.total_production_cost or 0,
            "total_produced": production_data.total_produced or 0,
            "marketplace_breakdown": [
                {
                    "name": r.name,
                    "icon": r.icon,
                    "qty": r.qty,
                    "revenue": r.revenue,
                    "profit": r.profit,
                    "orders": r.orders,
                }
                for r in marketplace_breakdown
            ],
            "product_breakdown": [
                {
                    "name": r.name,
                    "qty": r.qty,
                    "revenue": r.revenue,
                    "profit": r.profit,
                    "fee": r.fee,
                }
                for r in product_breakdown
            ],
        }

    @staticmethod
    def get_low_stock_products(db: Session, user_id: str = None) -> list:
        """Get products with stock below minimum."""
        query = db.query(Product).filter(
            Product.active == True,
            Product.stock <= Product.min_stock,
            Product.min_stock > 0,
        )
        if user_id:
            query = query.filter(Product.user_id == user_id)
        return query.order_by(Product.stock).all()

    @staticmethod
    def get_low_stock_materials(db: Session, user_id: str = None) -> list:
        """Get materials with stock below minimum."""
        query = db.query(Material).filter(
            Material.active == True,
            Material.stock <= Material.min_stock,
            Material.min_stock > 0,
        )
        if user_id:
            query = query.filter(Material.user_id == user_id)
        return query.order_by(Material.stock).all()

    @staticmethod
    def seed_default_marketplaces(db: Session) -> None:
        """Seed default Indonesian marketplaces."""
        existing = db.query(Marketplace).count()
        if existing > 0:
            return

        defaults = [
            {"name": "Shopee", "fee_percent": 5.0, "icon": "🟠", "settlement_days": 3},
            {"name": "Tokopedia", "fee_percent": 6.0, "icon": "🟢", "settlement_days": 2},
            {"name": "Lazada", "fee_percent": 4.5, "icon": "🔵", "settlement_days": 3},
            {"name": "Bukalapak", "fee_percent": 4.0, "icon": "🔴", "settlement_days": 2},
            {"name": "TikTok Shop", "fee_percent": 5.0, "icon": "🎵", "settlement_days": 3},
            {"name": "Offline/Toko", "fee_percent": 0, "icon": "🏪", "settlement_days": 0},
        ]

        for mp in defaults:
            marketplace = Marketplace(id=str(uuid.uuid4()), **mp)
            db.add(marketplace)
        db.commit()
        logger.info("Default marketplaces seeded.")
