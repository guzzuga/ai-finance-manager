"""Transaction and Report API routes — multi-tenant, filtered by user_id."""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.transaction_service import TransactionService
from app.services.report_service import ReportService
from app.utils.date_helpers import get_today, get_start_of_month, get_end_of_month

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["transactions"])


@router.get("/transactions")
def get_transactions(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    type_filter: Optional[str] = Query(None, alias="type"),
    db: Session = Depends(get_db),
):
    """Get transactions for a specific user."""
    from app.models.category import Category
    
    transactions = TransactionService.get_transactions(
        db, user_id, limit=limit, offset=offset, type_filter=type_filter
    )
    
    result = []
    for t in transactions:
        # Get category name
        category_name = "lainnya"
        if t.category_id:
            cat = db.query(Category).filter(Category.id == t.category_id).first()
            if cat:
                category_name = cat.name
        
        result.append({
            "id": t.id,
            "date": t.date,
            "type": t.type,
            "amount": t.amount,
            "note": t.note,
            "category": category_name,
            "quantity": t.quantity,
            "unit": t.unit,
            "price_per_unit": t.price_per_unit,
            "created_at": str(t.created_at),
        })
    
    return result


@router.get("/reports/summary")
def get_summary(
    user_id: str = Query(..., description="User ID"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get financial summary for a user."""
    today = get_today()
    start = start_date or get_start_of_month(today)
    end = end_date or get_end_of_month(today)
    
    summary = ReportService.get_summary(db, user_id, start, end)
    summary["start_date"] = start
    summary["end_date"] = end
    return summary


@router.get("/reports/cashflow")
def get_cashflow(
    user_id: str = Query(..., description="User ID"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get daily cashflow for a user."""
    from datetime import timedelta
    today = get_today()
    start = today - timedelta(days=days)
    
    daily = ReportService.get_daily_totals(db, user_id, start, today)
    return daily


@router.get("/reports/category-breakdown")
def get_category_breakdown(
    user_id: str = Query(..., description="User ID"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get category breakdown for a user."""
    today = get_today()
    start = start_date or get_start_of_month(today)
    end = end_date or get_end_of_month(today)
    
    breakdown = ReportService.get_category_breakdown(db, user_id, start, end)
    return breakdown


@router.post("/reset")
def reset_user_data(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Reset all transactions for a user and clear Google Sheets."""
    try:
        count = TransactionService.reset_user_data(db, user_id)
        return {
            "success": True,
            "message": f"Berhasil menghapus {count} transaksi",
            "deleted_count": count,
        }
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail="Gagal reset data")


class SheetsSyncRequest(BaseModel):
    tanggal: str
    jenis: str  # "pemasukan" or "pengeluaran"
    kategori: str
    nominal: int
    catatan: str
    sumber: str = "web"
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price_per_unit: Optional[int] = None


@router.post("/google-sheets/append")
def append_to_sheets(req: SheetsSyncRequest):
    """Append a transaction row to Google Sheets (called by dashboard)."""
    try:
        from app.services import google_sheets_service
        result = google_sheets_service.append_transaction(
            tanggal=req.tanggal,
            jenis=req.jenis,
            kategori=req.kategori,
            nominal=req.nominal,
            catatan=req.catatan,
            sumber=req.sumber,
            quantity=req.quantity,  # type: ignore[arg-type]
            unit=req.unit,  # type: ignore[arg-type]
            price_per_unit=req.price_per_unit,  # type: ignore[arg-type]
        )
        if result:
            return {"success": True, "message": "Synced to Google Sheets"}
        else:
            return {"success": False, "message": "Failed to sync to Google Sheets"}
    except Exception as e:
        logger.error(f"Sheets sync failed: {e}")
        return {"success": False, "message": str(e)}
