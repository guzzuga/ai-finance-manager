"""Konveksi API Router — endpoints for products, materials, marketplaces, sales, production."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.konveksi_service import KonveksiService

router = APIRouter(prefix="/api/konveksi", tags=["konveksi"])


# ==================== SCHEMAS ====================

class ProductCreate(BaseModel):
    name: str
    sku: Optional[str] = None
    category: Optional[str] = None
    hpp: int = 0
    price: int = 0
    stock: int = 0
    unit: str = "pcs"
    min_stock: int = 0
    notes: Optional[str] = None
    user_id: Optional[str] = None

class MaterialCreate(BaseModel):
    name: str
    unit: str = "meter"
    stock: float = 0
    price_per_unit: int = 0
    min_stock: float = 0
    supplier: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[str] = None

class MarketplaceCreate(BaseModel):
    name: str
    fee_percent: float = 0
    fee_fixed: int = 0
    icon: str = "🛒"
    settlement_days: int = 3
    notes: Optional[str] = None

class SaleCreate(BaseModel):
    user_id: str
    product_id: str
    marketplace_id: str
    date: str
    quantity: int = 1
    price_per_unit: int
    hpp_per_unit: int = 0
    shipping_cost: int = 0
    discount: int = 0
    order_id: Optional[str] = None
    notes: Optional[str] = None
    source: str = "web"

class ProductionCreate(BaseModel):
    user_id: str
    product_id: str
    date: str
    quantity: int
    cost_per_unit: int = 0
    notes: Optional[str] = None
    source: str = "web"


# ==================== PRODUCTS ====================

@router.get("/products")
def list_products(user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """List all products."""
    return KonveksiService.get_products(db, user_id=user_id)

@router.post("/products")
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product."""
    return KonveksiService.create_product(db, data.dict())

@router.get("/products/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)):
    """Get a single product."""
    product = KonveksiService.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.put("/products/{product_id}")
def update_product(product_id: str, data: dict, db: Session = Depends(get_db)):
    """Update a product."""
    product = KonveksiService.update_product(db, product_id, data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ==================== MATERIALS ====================

@router.get("/materials")
def list_materials(user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """List all materials."""
    return KonveksiService.get_materials(db, user_id=user_id)

@router.post("/materials")
def create_material(data: MaterialCreate, db: Session = Depends(get_db)):
    """Create a new material."""
    return KonveksiService.create_material(db, data.dict())

@router.put("/materials/{material_id}/stock")
def update_material_stock(material_id: str, quantity_change: float, db: Session = Depends(get_db)):
    """Update material stock."""
    material = KonveksiService.update_material_stock(db, material_id, quantity_change)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


# ==================== MARKETPLACES ====================

@router.get("/marketplaces")
def list_marketplaces(db: Session = Depends(get_db)):
    """List all marketplaces."""
    return KonveksiService.get_marketplaces(db)

@router.post("/marketplaces")
def create_marketplace(data: MarketplaceCreate, db: Session = Depends(get_db)):
    """Create a new marketplace."""
    return KonveksiService.create_marketplace(db, data.dict())


# ==================== SALES ====================

@router.get("/sales")
def list_sales(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    marketplace_id: Optional[str] = None,
    product_id: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """List sales with filters."""
    return KonveksiService.get_sales(
        db, user_id,
        start_date=start_date,
        end_date=end_date,
        marketplace_id=marketplace_id,
        product_id=product_id,
        limit=limit,
    )

@router.post("/sales")
def create_sale(data: SaleCreate, db: Session = Depends(get_db)):
    """Record a sale."""
    return KonveksiService.create_sale(db, data.dict())


# ==================== PRODUCTION ====================

@router.post("/production")
def create_production(data: ProductionCreate, db: Session = Depends(get_db)):
    """Record a production run."""
    return KonveksiService.create_production(db, data.dict())


# ==================== REPORTS ====================

@router.get("/reports/laporan")
def get_laporan_konveksi(
    user_id: str,
    start_date: str = Query(default=None),
    end_date: str = Query(default=None),
    db: Session = Depends(get_db),
):
    """Get konveksi profit/loss report."""
    if not start_date:
        start_date = date.today().replace(day=1).isoformat()
    if not end_date:
        end_date = date.today().isoformat()
    return KonveksiService.get_laporan_konveksi(db, user_id, start_date, end_date)

@router.get("/reports/low-stock")
def get_low_stock(user_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Get products and materials with low stock."""
    return {
        "products": KonveksiService.get_low_stock_products(db, user_id),
        "materials": KonveksiService.get_low_stock_materials(db, user_id),
    }
