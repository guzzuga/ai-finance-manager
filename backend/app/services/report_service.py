"""Report service — financial summaries and breakdowns."""
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.category import Category


class ReportService:
    """Service layer for financial reports."""

    @staticmethod
    def get_summary(db: Session, user_id: str, start_date: date, end_date: date) -> dict:
        """Get total pemasukan, pengeluaran, and saldo for a period."""
        results = (
            db.query(
                Transaction.type,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.date >= str(start_date),
                Transaction.date <= str(end_date),
            )
            .group_by(Transaction.type)
            .all()
        )

        pemasukan = 0
        pengeluaran = 0
        count_in = 0
        count_out = 0

        for r in results:
            if r.type == "pemasukan":
                pemasukan = r.total or 0
                count_in = r.count or 0
            elif r.type == "pengeluaran":
                pengeluaran = r.total or 0
                count_out = r.count or 0

        return {
            "pemasukan": pemasukan,
            "pengeluaran": pengeluaran,
            "saldo": pemasukan - pengeluaran,
            "total_transaksi": count_in + count_out,
        }

    @staticmethod
    def get_category_breakdown(db: Session, user_id: str, start_date: date, end_date: date) -> list:
        """Get spending/income breakdown by category."""
        results = (
            db.query(
                Category.name,
                Category.icon,
                Transaction.type,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .join(Category, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == user_id,
                Transaction.date >= str(start_date),
                Transaction.date <= str(end_date),
            )
            .group_by(Category.name, Category.icon, Transaction.type)
            .order_by(func.sum(Transaction.amount).desc())
            .all()
        )

        return [
            {
                "category": r.name,
                "icon": r.icon,
                "type": r.type,
                "total": r.total,
                "count": r.count,
            }
            for r in results
        ]

    @staticmethod
    def get_daily_totals(db: Session, user_id: str, start_date: date, end_date: date) -> list:
        """Get daily pemasukan and pengeluaran totals."""
        results = (
            db.query(
                Transaction.date,
                Transaction.type,
                func.sum(Transaction.amount).label("total"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.date >= str(start_date),
                Transaction.date <= str(end_date),
            )
            .group_by(Transaction.date, Transaction.type)
            .order_by(Transaction.date)
            .all()
        )

        daily = {}
        for r in results:
            if r.date not in daily:
                daily[r.date] = {"date": r.date, "pemasukan": 0, "pengeluaran": 0}
            daily[r.date][r.type] = r.total

        return list(daily.values())

    @staticmethod
    def get_monthly_totals(db: Session, user_id: str, year: int) -> list:
        """Get monthly totals for a given year."""
        results = (
            db.query(
                func.substr(Transaction.date, 1, 7).label("month"),
                Transaction.type,
                func.sum(Transaction.amount).label("total"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.date.like(f"{year}-%"),
            )
            .group_by("month", Transaction.type)
            .order_by("month")
            .all()
        )

        monthly = {}
        for r in results:
            if r.month not in monthly:
                monthly[r.month] = {"month": r.month, "pemasukan": 0, "pengeluaran": 0}
            monthly[r.month][r.type] = r.total

        return list(monthly.values())

    @staticmethod
    def get_recent_transactions(db: Session, user_id: str, limit: int = 10) -> list:
        """Get the most recent transactions."""
        return (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id)
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())
            .limit(limit)
            .all()
        )
