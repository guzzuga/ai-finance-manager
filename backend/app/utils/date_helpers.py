"""Date helper utilities with Asia/Jakarta timezone support."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Asia/Jakarta")


def get_today() -> date:
    """Get today's date in Asia/Jakarta timezone."""
    return datetime.now(TIMEZONE).date()


def get_start_of_month(d: date = None) -> date:
    """Get the first day of the month for the given date."""
    if d is None:
        d = get_today()
    return d.replace(day=1)


def get_end_of_month(d: date = None) -> date:
    """Get the last day of the month for the given date."""
    if d is None:
        d = get_today()
    if d.month == 12:
        next_month_first = date(d.year + 1, 1, 1)
    else:
        next_month_first = date(d.year, d.month + 1, 1)
    return next_month_first - timedelta(days=1)


def get_start_of_week(d: date = None) -> date:
    """Get the first day (Monday) of the current week."""
    if d is None:
        d = get_today()
    return d - timedelta(days=d.weekday())


def parse_date_range(period: str) -> tuple[date, date]:
    """Parse a human-readable period string into a (start_date, end_date) tuple."""
    today = get_today()
    p = period.strip().lower()

    if p == "hari ini":
        return today, today
    if p == "kemarin":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    if p == "minggu ini":
        start = today - timedelta(days=today.weekday())
        return start, today
    if p == "bulan ini":
        return get_start_of_month(today), today
    if p == "bulan lalu":
        first_this_month = get_start_of_month(today)
        last_month_end = first_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start, last_month_end

    raise ValueError(f"Periode tidak dikenali: '{period}'")
