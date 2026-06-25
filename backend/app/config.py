"""Configuration — loads from .env and defines defaults."""
import os
from dotenv import load_dotenv

load_dotenv()

# App
APP_NAME = "AI Finance Manager"
APP_VERSION = "1.0.0"

# MiMo AI API
MIMO_API_KEY = os.getenv("MIMO_API_KEY", "")
MIMO_BASE_URL = os.getenv("MIMO_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1")
MIMO_MODEL = os.getenv("MIMO_MODEL", "mimo-v2.5-pro")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/finance.db")

# Maton API (Google Sheets)
MATON_API_KEY = os.getenv("MATON_API_KEY", "")
MATON_CONN_ID = os.getenv("MATON_CONN_ID", "fb38cb52-9379-452c-8ead-30a3507e8f5c")
SHEET_PEMASUKAN = os.getenv("SHEET_PEMASUKAN", "1Dllu_MVlpxtYb19E_NA9nsOSPruvXuK29QM4tDm1xtg")
SHEET_PENGELUARAN = os.getenv("SHEET_PENGELUARAN", "1S_tOg_QdZgMV37Wm5Flzu2_c31IFZwqLSgzJ4RmIom0")

# Default categories
DEFAULT_CATEGORIES = [
    # Pengeluaran
    {"name": "makanan", "type": "pengeluaran", "icon": "🍚", "keywords": ["makan", "nasi", "mie", "soto", "bakso", "ayam", "ikan", "roti", "snack", "jajan", "kopi", "teh", "minum", "es", "buah", "sayur"]},
    {"name": "transport", "type": "pengeluaran", "icon": "🚗", "keywords": ["grab", "gojek", "ojek", "bensin", "parkir", "tol", "bus", "kereta", "taxi", "angkot", "bensin", "solar"]},
    {"name": "rumah", "type": "pengeluaran", "icon": "🏠", "keywords": ["listrik", "air", "gas", "internet", "wifi", "kos", "kontrakan", "sewa", "perbaikan", "bersih"]},
    {"name": "belanja", "type": "pengeluaran", "icon": "🛒", "keywords": ["belanja", "supermarket", "minimarket", "indomaret", "alfamart", "pasar", "toko"]},
    {"name": "pakaian", "type": "pengeluaran", "icon": "👕", "keywords": ["baju", "celana", "sepatu", "sandal", "jaket", "topi", "kaus", "kemeja"]},
    {"name": "kesehatan", "type": "pengeluaran", "icon": "💊", "keywords": ["obat", "dokter", "rumah sakit", "apotek", "vitamin", "masker", "hand sanitizer"]},
    {"name": "hiburan", "type": "pengeluaran", "icon": "🎮", "keywords": ["nonton", "bioskop", "game", "netflix", "spotify", "karaoke", "liburan", "wisata"]},
    {"name": "pendidikan", "type": "pengeluaran", "icon": "📚", "keywords": ["buku", "sekolah", "kursus", "les", "kuliah", "ujian", "alat tulis"]},
    {"name": "komunikasi", "type": "pengeluaran", "icon": "📱", "keywords": ["pulsa", "kuota", "internet", "telepon", "sms", "paket data"]},
    {"name": "lainnya", "type": "pengeluaran", "icon": "📦", "keywords": ["lainnya", "lain", "dll", "lain-lain"]},
    # Pemasukan
    {"name": "gaji", "type": "pemasukan", "icon": "💰", "keywords": ["gaji", "gajian", "salary", "upah", "honorer"]},
    {"name": "freelance", "type": "pemasukan", "icon": "💻", "keywords": ["freelance", "proyek", "project", "order", "pesanan"]},
    {"name": "jualan", "type": "pemasukan", "icon": "🛍️", "keywords": ["jualan", "jual", "dagang", "toko", "lapak", "olshop"]},
    {"name": "transfer_masuk", "type": "pemasukan", "icon": "📥", "keywords": ["transfer", "kiriman", "terima", "masuk"]},
    {"name": "investasi", "type": "pemasukan", "icon": "📈", "keywords": ["dividen", "bunga", "saham", "crypto", "deposito"]},
    {"name": "lainnya_masuk", "type": "pemasukan", "icon": "💵", "keywords": ["cashback", "refund", "bonus", "THR", "hadiah"]},
]
