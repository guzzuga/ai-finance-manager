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

from app.config import MATON_API_KEY, MATON_CONN_ID, SHEET_PEMASUKAN
# SHEET_PENGELUARAN deprecated — all data now in SHEET_PEMASUKAN with separate tabs

logger = logging.getLogger(__name__)

BASE_URL = "https://api.maton.ai/google-sheets/v4/spreadsheets"

# Layout constants
HEADER_ROWS = 6
DATA_START_ROW = 7
COL_RANGE = "A:G"

# Konveksi sheet names (within SHEET_PEMASUKAN spreadsheet)
SHEET_PENJUALAN = "Penjualan_Konveksi"
SHEET_PRODUKSI = "Produksi"
SHEET_BAHAN = "Bahan_Baku"
KONVEKSI_DATA_START = 4  # Row 4 for konveksi sheets (header at row 3)


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
    """Get the correct spreadsheet ID. All data is now in one spreadsheet."""
    return SHEET_PEMASUKAN


def _find_next_row(sheet_id: str, tab_name: str = "Pemasukan") -> int:
    """Find the next empty data row in the specified tab."""
    result = _make_request(sheet_id, f"/values/{tab_name}!B{DATA_START_ROW}:B2000")
    values = result.get("values", [])
    last_occupied = DATA_START_ROW - 1
    for i, row in enumerate(values):
        cell = str(row[0]).strip() if row and row[0] else ""
        if cell and not cell.startswith("="):
            last_occupied = DATA_START_ROW + i
    return last_occupied + 1


def setup_konveksi_headers() -> bool:
    """Set up headers for konveksi sheets (Penjualan_Konveksi, Produksi, Bahan_Baku)."""
    # Penjualan_Konveksi
    _make_request(SHEET_PEMASUKAN, "/values/" + SHEET_PENJUALAN + "!A1:N1?valueInputOption=USER_ENTERED", "PUT", {
        "values": [["PENJUALAN KONVEKSI", "", "", "", "", "", "", "", "", "", "", "", "", ""]]
    })
    _make_request(SHEET_PEMASUKAN, "/values/" + SHEET_PENJUALAN + "!A3:N3?valueInputOption=USER_ENTERED", "PUT", {
        "values": [["No", "Tanggal", "Produk", "Marketplace", "Qty", "Harga/Unit", "Revenue", "HPP", "Fee", "Ongkir", "Laba", "Order ID", "Status", "Tgl Cair"]]
    })
    # Produksi
    _make_request(SHEET_PEMASUKAN, "/values/" + SHEET_PRODUKSI + "!A1:G1?valueInputOption=USER_ENTERED", "PUT", {
        "values": [["PRODUKSI", "", "", "", "", "", ""]]
    })
    _make_request(SHEET_PEMASUKAN, "/values/" + SHEET_PRODUKSI + "!A3:G3?valueInputOption=USER_ENTERED", "PUT", {
        "values": [["No", "Tanggal", "Produk", "Qty", "Biaya/Unit", "Total Biaya", "Catatan"]]
    })
    # Bahan_Baku
    _make_request(SHEET_PEMASUKAN, "/values/" + SHEET_BAHAN + "!A1:I1?valueInputOption=USER_ENTERED", "PUT", {
        "values": [["BAHAN BAKU", "", "", "", "", "", "", "", ""]]
    })
    _make_request(SHEET_PEMASUKAN, "/values/" + SHEET_BAHAN + "!A3:I3?valueInputOption=USER_ENTERED", "PUT", {
        "values": [["No", "Tanggal", "Nama", "Satuan", "Qty", "Harga/Unit", "Total", "Supplier", "Catatan"]]
    })
    logger.info("Konveksi sheet headers set up")
    return True


def setup_headers() -> bool:
    """Set up headers for Pemasukan and Pengeluaran tabs (single spreadsheet)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    for label in ["Pemasukan", "Pengeluaran"]:
        upper = label.upper()

        _make_request(SHEET_PEMASUKAN, f"/values/{label}!A1:J1?valueInputOption=USER_ENTERED", "PUT", {
            "values": [[f"LAPORAN {upper} — AGUS COLLECTION", "", "", "", "", "", "", "", "", ""]]
        })
        _make_request(SHEET_PEMASUKAN, f"/values/{label}!A2:J2?valueInputOption=USER_ENTERED", "PUT", {
            "values": [[f"Periode: Semua  |  Dicetak: {now}", "", "", "", "", "", "", "", "", ""]]
        })
        _make_request(SHEET_PEMASUKAN, f"/values/{label}!A3:J3?valueInputOption=USER_ENTERED", "PUT", {
            "values": [[f"Total {label}", "", "", "Jumlah Transaksi", "", "Rata-rata/Transaksi", "", "", "", ""]]
        })
        _make_request(SHEET_PEMASUKAN, f"/values/{label}!A4:F4?valueInputOption=USER_ENTERED", "PUT", {
            "values": [[
                f'=SUM(E{DATA_START_ROW}:E2000)', "", "",
                f'=COUNTA(B{DATA_START_ROW}:B2000)', "",
                f'=IFERROR(AVERAGE(E{DATA_START_ROW}:E2000); 0)'
            ]]
        })
        _make_request(SHEET_PEMASUKAN, f"/values/{label}!A5:J5?valueInputOption=USER_ENTERED", "PUT", {
            "values": [["No", "Tanggal", "Kategori", "Deskripsi", "Nominal (Rp)", "Jumlah", "Satuan", "Harga/Satuan", "Sumber", "Status"]]
        })
        _make_request(SHEET_PEMASUKAN, f"/values/{label}!A6:J6?valueInputOption=USER_ENTERED", "PUT", {
            "values": [["", "", "", "TOTAL", f"=SUM(E{DATA_START_ROW}:E2000)", "", "", "", "", ""]]
        })

        logger.info(f"✅ {label} tab headers set (rows 1-6)")

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
    """Append a transaction row to the correct tab (Pemasukan or Pengeluaran)."""
    sheet_id = _get_sheet_id(jenis)
    tab_name = "Pemasukan" if jenis == "pemasukan" else "Pengeluaran"
    next_row = _find_next_row(sheet_id, tab_name)
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
        f"/values/{tab_name}!A{next_row}:J{next_row}?valueInputOption=USER_ENTERED",
        method="PUT",
        data={"values": row},
    )

    if "error" in result:
        logger.error(f"Failed to append to Sheets: {result['error']}")
        return False

    logger.info(f"✅ Appended {jenis} #{nomor} to sheet at row {next_row}")
    return True


def get_all_data(jenis: str = "pengeluaran") -> list:
    """Read all data from a tab."""
    tab_name = "Pemasukan" if jenis == "pemasukan" else "Pengeluaran"
    result = _make_request(SHEET_PEMASUKAN, f"/values/{tab_name}!A1:J2000")
    return result.get("values", [])


def clear_data(jenis: str = None) -> bool:
    """Clear data rows (keep headers) from Pemasukan and/or Pengeluaran tabs."""
    tabs_to_clear = []
    if jenis is None:
        tabs_to_clear = ["Pemasukan", "Pengeluaran"]
    else:
        tabs_to_clear = ["Pemasukan" if jenis == "pemasukan" else "Pengeluaran"]
    
    for tab in tabs_to_clear:
        empty_rows = [["", "", "", "", "", "", "", "", "", ""] for _ in range(1994)]
        result = _make_request(
            SHEET_PEMASUKAN,
            f"/values/{tab}!A7:J2000?valueInputOption=USER_ENTERED",
            method="PUT",
            data={"values": empty_rows},
        )
        if "error" in result:
            logger.error(f"Failed to clear {tab}: {result['error']}")
            return False
        
        # Re-set TOTAL formula
        _make_request(
            SHEET_PEMASUKAN,
            f"/values/{tab}!A6:J6?valueInputOption=USER_ENTERED",
            method="PUT",
            data={"values": [["", "", "", "TOTAL", f"=SUM(E{DATA_START_ROW}:E2000)", "", "", "", "", ""]]},
        )
        
        logger.info(f"✅ {tab} tab cleared (headers preserved)")
    
    return True


# ==================== KONVEKSI SHEET FUNCTIONS ====================

def _find_next_konveksi_row(sheet_tab: str) -> int:
    """Find the next empty row in a konveksi sheet tab."""
    result = _make_request(SHEET_PEMASUKAN, f"/values/{sheet_tab}!B{KONVEKSI_DATA_START}:B2000")
    values = result.get("values", [])
    last_occupied = KONVEKSI_DATA_START - 1
    for i, row in enumerate(values):
        cell = str(row[0]).strip() if row and row[0] else ""
        if cell and not cell.startswith("="):
            last_occupied = KONVEKSI_DATA_START + i
    return last_occupied + 1


def append_penjualan(
    tanggal: str, produk: str, marketplace: str, qty: int,
    harga_per_unit: int, revenue: int, hpp: int, fee: int,
    ongkir: int, laba: int, order_id: str = "", status: str = "completed",
    tgl_cair: str = "",
) -> bool:
    """Append a sale record to the Penjualan_Konveksi sheet."""
    next_row = _find_next_konveksi_row(SHEET_PENJUALAN)
    nomor = next_row - (KONVEKSI_DATA_START - 1)

    row = [[
        nomor, tanggal, produk, marketplace, qty, harga_per_unit,
        revenue, hpp, fee, ongkir, laba, order_id, status, tgl_cair,
    ]]
    result = _make_request(
        SHEET_PEMASUKAN,
        f"/values/{SHEET_PENJUALAN}!A{next_row}:N{next_row}?valueInputOption=USER_ENTERED",
        method="PUT",
        data={"values": row},
    )
    if "error" in result:
        logger.error(f"Failed to append penjualan: {result['error']}")
        return False
    logger.info(f"✅ Penjualan #{nomor} appended to sheet")
    return True


def append_produksi(
    tanggal: str, produk: str, qty: int,
    biaya_per_unit: int, total_biaya: int, catatan: str = "",
) -> bool:
    """Append a production record to the Produksi sheet."""
    next_row = _find_next_konveksi_row(SHEET_PRODUKSI)
    nomor = next_row - (KONVEKSI_DATA_START - 1)

    row = [[nomor, tanggal, produk, qty, biaya_per_unit, total_biaya, catatan]]
    result = _make_request(
        SHEET_PEMASUKAN,
        f"/values/{SHEET_PRODUKSI}!A{next_row}:G{next_row}?valueInputOption=USER_ENTERED",
        method="PUT",
        data={"values": row},
    )
    if "error" in result:
        logger.error(f"Failed to append produksi: {result['error']}")
        return False
    logger.info(f"✅ Produksi #{nomor} appended to sheet")
    return True


def append_bahan_baku(
    tanggal: str, nama: str, unit: str, qty: float,
    harga_per_unit: int, total: int, supplier: str = "", catatan: str = "",
) -> bool:
    """Append a material purchase to the Bahan_Baku sheet."""
    next_row = _find_next_konveksi_row(SHEET_BAHAN)
    nomor = next_row - (KONVEKSI_DATA_START - 1)

    row = [[nomor, tanggal, nama, unit, qty, harga_per_unit, total, supplier, catatan]]
    result = _make_request(
        SHEET_PEMASUKAN,
        f"/values/{SHEET_BAHAN}!A{next_row}:I{next_row}?valueInputOption=USER_ENTERED",
        method="PUT",
        data={"values": row},
    )
    if "error" in result:
        logger.error(f"Failed to append bahan baku: {result['error']}")
        return False
    logger.info(f"✅ Bahan baku #{nomor} appended to sheet")
    return True


def clear_konveksi_data() -> bool:
    """Clear all konveksi sheets (Penjualan_Konveksi, Produksi, Bahan_Baku). Keep headers."""
    konveksi_sheets = [
        ("Penjualan_Konveksi", SHEET_PENJUALAN, "N"),  # 14 columns A-N
        ("Produksi", SHEET_PRODUKSI, "G"),              # 7 columns A-G
        ("Bahan_Baku", SHEET_BAHAN, "I"),               # 9 columns A-I
    ]
    
    for label, sheet_name, end_col in konveksi_sheets:
        col_count = ord(end_col) - ord('A') + 1
        empty_rows = [[""] * col_count for _ in range(1997)]
        result = _make_request(
            SHEET_PEMASUKAN,
            f"/values/{sheet_name}!A4:{end_col}2000?valueInputOption=USER_ENTERED",
            method="PUT",
            data={"values": empty_rows},
        )
        if "error" in result:
            logger.error(f"Failed to clear {label}: {result['error']}")
            return False
        logger.info(f"✅ {label} sheet cleared")
    
    return True
