"""Google Sheets integration — auto-append to separate income/expense sheets.

Sheet structure (improved formatting):
  Row 1: Title          — e.g. "LAPORAN PEMASUKAN — AGUS COLLECTION"
  Row 2: Period filter   — e.g. "Periode: Semua | Dicetak: 2026-06-23"
  Row 3: Summary labels  — Total | Jumlah Transaksi | Rata-rata
  Row 4: Summary values  — (formulas: SUM, COUNTA, AVERAGE)
  Row 5: Column headers  — No | Tanggal | Kategori | Deskripsi | Nominal (Rp) | Sumber | Status
  Row 6: TOTAL row       — (blank) | (blank) | (blank) | TOTAL | =SUM(E7:E2000) | (blank) | (blank)
  Row 7+: Data rows      — (auto-numbered, newest at bottom)
"""
import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime

from app.config import MATON_API_KEY, MATON_CONN_ID, SHEET_PEMASUKAN, SHEET_PENGELUARAN

logger = logging.getLogger(__name__)

BASE_URL = "https://api.maton.ai/google-sheets/v4/spreadsheets"

# Layout constants
HEADER_ROWS = 6
DATA_START_ROW = 7
COL_RANGE = "A:G"


def _make_request(sheet_id: str, path: str, method: str = "GET", data: dict = None) -> dict:
    """Make authenticated request to Google Sheets via Maton."""
    url = f"{BASE_URL}/{sheet_id}{path}"
    body = json.dumps(data).encode() if data else None

    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {MATON_API_KEY}")
    req.add_header("Maton-Connection", MATON_CONN_ID)
    if body:
        req.add_header("Content-Type", "application/json")

    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        logger.error(f"Sheets API error: {e.code} - {e.read().decode()}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Sheets request error: {e}")
        return {"error": str(e)}


def _get_sheet_id(jenis: str) -> str:
    """Get the correct spreadsheet ID based on transaction type."""
    if jenis == "pemasukan":
        return SHEET_PEMASUKAN
    return SHEET_PENGELUARAN


def _find_next_row(sheet_id: str) -> int:
    """Find the next empty data row."""
    result = _make_request(sheet_id, f"/values/Sheet1!B{DATA_START_ROW}:B2000")
    values = result.get("values", [])
    last_occupied = DATA_START_ROW - 1
    for i, row in enumerate(values):
        cell = str(row[0]).strip() if row and row[0] else ""
        if cell and not cell.startswith("="):
            last_occupied = DATA_START_ROW + i
    return last_occupied + 1


def setup_headers() -> bool:
    """Set up the full header structure on both sheets."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    for label, sid in [("Pemasukan", SHEET_PEMASUKAN), ("Pengeluaran", SHEET_PENGELUARAN)]:
        upper = label.upper()

        # Row 1 — Title
        _make_request(sid, "/values/Sheet1!A1:J1?valueInputOption=USER_ENTERED", "PUT", {
            "values": [[f"LAPORAN {upper} — AGUS COLLECTION", "", "", "", "", "", "", "", "", ""]]
        })

        # Row 2 — Period / timestamp
        _make_request(sid, "/values/Sheet1!A2:J2?valueInputOption=USER_ENTERED", "PUT", {
            "values": [[f"Periode: Semua  |  Dicetak: {now}", "", "", "", "", "", "", "", "", ""]]
        })

        # Row 3 — Summary labels
        _make_request(sid, "/values/Sheet1!A3:J3?valueInputOption=USER_ENTERED", "PUT", {
            "values": [
                [f"Total {label}", "", "", "Jumlah Transaksi", "", "Rata-rata/Transaksi", "", "", "", ""]
            ]
        })

        # Row 4 — Summary formulas
        _make_request(sid, "/values/Sheet1!A4:J4?valueInputOption=USER_ENTERED", "PUT", {
            "values": [[
                f'=SUM(E{DATA_START_ROW}:E2000)', "", "",
                f'=COUNTA(B{DATA_START_ROW}:B2000)', "",
                f'=IF(COUNTA(B{DATA_START_ROW}:B2000)>0, SUM(E{DATA_START_ROW}:E2000)/COUNTA(B{DATA_START_ROW}:B2000), 0)', "",
                "", "", ""
            ]]
        })

        # Row 5 — Column headers
        _make_request(sid, "/values/Sheet1!A5:J5?valueInputOption=USER_ENTERED", "PUT", {
            "values": [[
                "No", "Tanggal", "Kategori", "Deskripsi", "Nominal (Rp)", "Jumlah", "Satuan", "Harga/Satuan", "Sumber", "Status"
            ]]
        })

        # Row 6 — TOTAL row
        _make_request(sid, f"/values/Sheet1!A6:J6?valueInputOption=USER_ENTERED", "PUT", {
            "values": [[
                "", "", "", "TOTAL", f"=SUM(E{DATA_START_ROW}:E2000)", "", "", "", "", ""
            ]]
        })

        logger.info(f"✅ {label} sheet headers set (rows 1-6)")

    return True


def append_transaction(
    tanggal: str,
    jenis: str,
    kategori: str,
    nominal: int,
    catatan: str,
    sumber: str = "telegram",
    quantity: float = None,
    unit: str = None,
    price_per_unit: int = None,
) -> bool:
    """Append a transaction row to the correct sheet."""
    sheet_id = _get_sheet_id(jenis)
    next_row = _find_next_row(sheet_id)
    nomor = next_row - (DATA_START_ROW - 1)

    row = [[
        nomor,            # A — No
        tanggal,          # B — Tanggal
        kategori,         # C — Kategori
        catatan,          # D — Deskripsi
        nominal,          # E — Nominal (Rp)
        quantity if quantity else "",  # F — Jumlah
        unit if unit else "",          # G — Satuan
        price_per_unit if price_per_unit else "",  # H — Harga/Satuan
        sumber,           # I — Sumber
        "Tercatat",       # J — Status
    ]]
    result = _make_request(
        sheet_id,
        f"/values/Sheet1!A{next_row}:J{next_row}?valueInputOption=USER_ENTERED",
        method="PUT",
        data={"values": row},
    )

    if "error" in result:
        logger.error(f"Failed to append to Sheets: {result['error']}")
        return False

    logger.info(f"✅ Appended {jenis} #{nomor} to sheet at row {next_row}")
    return True


def get_all_data(jenis: str = "pengeluaran") -> list:
    """Read all data from a sheet."""
    sheet_id = _get_sheet_id(jenis)
    result = _make_request(sheet_id, "/values/Sheet1!A1:G2000")
    return result.get("values", [])


def clear_data(jenis: str = None) -> bool:
    """Clear all data rows (keep headers) from one or both sheets.
    
    Args:
        jenis: 'pemasukan', 'pengeluaran', or None (clear both)
    """
    sheets_to_clear = []
    if jenis is None:
        sheets_to_clear = [("Pemasukan", SHEET_PEMASUKAN), ("Pengeluaran", SHEET_PENGELUARAN)]
    else:
        label = "Pemasukan" if jenis == "pemasukan" else "Pengeluaran"
        sheets_to_clear = [(label, _get_sheet_id(jenis))]
    
    for label, sid in sheets_to_clear:
        # Generate empty rows to fill data area (row 7 to 2000 = 1994 rows)
        empty_rows = [["", "", "", "", "", "", "", "", "", ""] for _ in range(1994)]
        
        # Clear data rows by overwriting with empty values
        result = _make_request(
            sid,
            "/values/Sheet1!A7:J2000?valueInputOption=USER_ENTERED",
            method="PUT",
            data={"values": empty_rows},
        )
        if "error" in result:
            logger.error(f"Failed to clear {label} sheet: {result['error']}")
            return False
        
        # Re-set the TOTAL formula in row 6
        _make_request(
            sid,
            "/values/Sheet1!A6:J6?valueInputOption=USER_ENTERED",
            method="PUT",
            data={"values": [["", "", "", "TOTAL", f"=SUM(E{DATA_START_ROW}:E2000)", "", "", "", "", ""]]},
        )
        
        logger.info(f"✅ {label} sheet cleared (headers preserved)")
    
    return True
