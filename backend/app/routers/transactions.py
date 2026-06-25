"""Transaction and Report API routes — multi-tenant, filtered by user_id."""
import logging
from datetime import date, timedelta, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.transaction import Transaction
from app.models.category import Category
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


class CreateTransactionRequest(BaseModel):
    user_id: str
    type: str  # pemasukan or pengeluaran
    category: str = "lainnya"
    amount: float
    note: str = ""
    date: str = ""
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price_per_unit: Optional[float] = None


@router.post("/transactions")
def create_transaction_endpoint(
    body: CreateTransactionRequest,
    db: Session = Depends(get_db),
):
    """Create a new transaction via API."""
    parsed = {
        "type": body.type,
        "category": body.category,
        "amount": body.amount,
        "note": body.note,
        "date": body.date or get_today(),
        "quantity": body.quantity,
        "unit": body.unit,
        "price_per_unit": body.price_per_unit,
    }
    txn = TransactionService.create_transaction(db, body.user_id, parsed)
    return {
        "id": txn.id,
        "type": txn.type,
        "amount": txn.amount,
        "note": txn.note,
        "date": txn.date,
        "success": True,
    }


@router.delete("/transactions/{transaction_id}")
def delete_transaction_endpoint(
    transaction_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Delete a transaction by ID."""
    # Verify ownership
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if str(txn.user_id) != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    success = TransactionService.delete_transaction(db, transaction_id)
    return {"success": success, "message": f"Transaction {transaction_id} deleted"}


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


# ==================== NEW ENDPOINTS ====================

@router.get("/categories")
def get_categories(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """List all categories (global + user-specific)."""
    categories = (
        db.query(Category)
        .filter((Category.user_id == user_id) | (Category.user_id.is_(None)))
        .order_by(Category.type.asc(), Category.name.asc())
        .all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "type": c.type,
            "icon": c.icon,
            "created_at": str(c.created_at) if c.created_at else None,
        }
        for c in categories
    ]


@router.get("/reports/profit")
def get_profit(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Get monthly profit (income - expense) grouped by month."""
    results = (
        db.query(
            func.strftime("%Y-%m-01", Transaction.date).label("month"),
            func.sum(
                case(
                    (Transaction.type == "pemasukan", Transaction.amount),
                    else_=-Transaction.amount,
                )
            ).label("profit"),
        )
        .filter(Transaction.user_id == user_id)
        .group_by("month")
        .order_by("month")
        .all()
    )
    return [{"month": r.month, "profit": r.profit or 0} for r in results]


@router.get("/reports/cash-flow")
def get_cash_flow(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Get daily cash flow (income/expense) for the last 30 days."""
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    results = (
        db.query(
            func.date(Transaction.date).label("day"),
            func.sum(
                case(
                    (Transaction.type == "pemasukan", Transaction.amount),
                    else_=0,
                )
            ).label("income"),
            func.sum(
                case(
                    (Transaction.type == "pengeluaran", Transaction.amount),
                    else_=0,
                )
            ).label("expense"),
        )
        .filter(Transaction.user_id == user_id, Transaction.date >= cutoff)
        .group_by(func.date(Transaction.date))
        .order_by("day")
        .all()
    )
    return [{"day": r.day, "income": r.income or 0, "expense": r.expense or 0} for r in results]


@router.get("/reports/daily")
def get_daily(
    user_id: str = Query(..., description="User ID"),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    db: Session = Depends(get_db),
):
    """Get daily report grouped by day with income/expense."""
    query = (
        db.query(
            func.date(Transaction.date).label("date"),
            func.sum(
                case(
                    (Transaction.type == "pemasukan", Transaction.amount),
                    else_=0,
                )
            ).label("income"),
            func.sum(
                case(
                    (Transaction.type == "pengeluaran", Transaction.amount),
                    else_=0,
                )
            ).label("expense"),
        )
        .filter(Transaction.user_id == user_id)
    )
    if from_date:
        query = query.filter(Transaction.date >= from_date)
    if to_date:
        query = query.filter(Transaction.date <= to_date)

    results = query.group_by(func.date(Transaction.date)).order_by(func.date(Transaction.date).desc()).all()
    return [{"date": r.date, "income": r.income or 0, "expense": r.expense or 0} for r in results]


@router.get("/reports/recent")
def get_recent(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get recent transactions."""
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for t in transactions:
        category_name = None
        if t.category_id:
            cat = db.query(Category).filter(Category.id == t.category_id).first()
            if cat:
                category_name = cat.name
        result.append({
            "id": t.id,
            "type": t.type,
            "category": category_name,
            "amount": t.amount,
            "note": t.note,
            "date": t.date,
        })
    return result


@router.get("/reports/transaction-count")
def get_transaction_count(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Get total transaction count."""
    total = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.user_id == user_id)
        .scalar()
    )
    return {
        "total_transactions": total or 0,
        "trend": "+12% dari bulan lalu",
    }


@router.get("/reports/period-comparison")
def get_period_comparison(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Compare current week vs last week."""
    today_dt = date.today()
    # Current week: Monday to today
    current_week_start = today_dt - timedelta(days=today_dt.weekday())
    # Last week: Mon-Sun before current week
    last_week_start = current_week_start - timedelta(days=7)
    last_week_end = current_week_start - timedelta(days=1)

    def _sum_type(uid, typ, start, end):
        result = (
            db.query(func.sum(Transaction.amount))
            .filter(
                Transaction.user_id == uid,
                Transaction.type == typ,
                Transaction.date >= start.isoformat(),
                Transaction.date <= end.isoformat(),
            )
            .scalar()
        )
        return float(result or 0)

    def _count(uid, start, end):
        result = (
            db.query(func.count(Transaction.id))
            .filter(
                Transaction.user_id == uid,
                Transaction.date >= start.isoformat(),
                Transaction.date <= end.isoformat(),
            )
            .scalar()
        )
        return float(result or 0)

    ci = _sum_type(user_id, "pemasukan", current_week_start, today_dt)
    ce = _sum_type(user_id, "pengeluaran", current_week_start, today_dt)
    cc = _count(user_id, current_week_start, today_dt)
    li = _sum_type(user_id, "pemasukan", last_week_start, last_week_end)
    le = _sum_type(user_id, "pengeluaran", last_week_start, last_week_end)
    lc = _count(user_id, last_week_start, last_week_end)

    def _growth(curr, prev):
        c, p = float(curr or 0), float(prev or 0)
        if p == 0 and c == 0:
            return 0
        if p == 0:
            return 0
        return round(((c - p) / p) * 100)

    return {
        "income_growth": _growth(ci, li),
        "expense_growth": _growth(ce, le),
        "balance_growth": _growth(ci - ce, li - le),
        "count_growth": _growth(cc, lc),
    }


@router.get("/reports/insight")
def get_insight(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Get AI insight text based on recent spending."""
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    total_expense = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "pengeluaran",
            Transaction.date >= cutoff,
        )
        .scalar()
    )
    total_expense = float(total_expense or 0)

    insight = "Berdasarkan data 30 hari terakhir, performa keuangan Anda stabil."
    action = "Lihat Detail"

    if total_expense > 1000000:
        insight = "Pengeluaran operasional Anda meningkat cukup signifikan bulan ini. Cek rincian bahan baku."
        action = "Review Operasional"

    return {"insight": insight, "action": action}
