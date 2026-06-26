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

# Default categories — KONVEKSI BUSINESS
DEFAULT_CATEGORIES = [
    # Pengeluaran (Biaya Bisnis)
    {"name": "bahan_baku", "type": "pengeluaran", "icon": "🧵", "keywords": ["kain", "benang", "kancing", "resleting", "furing", "label", "bahan", "kain katun", "kain tropical", "kain drill", "kain oxford", "kain satin", "kain blacu", "interfacing", "vlieseline"]},
    {"name": "biaya_produksi", "type": "pengeluaran", "icon": "🏭", "keywords": ["jahit", "sablon", "potong", "obras", "setrika", "qc", "produksi", "upah jahit", "upah potong", "upah sablon", "upah obras", "konveksi", "penjahit", "tukang jahit"]},
    {"name": "operasional", "type": "pengeluaran", "icon": "⚙️", "keywords": ["listrik", "air", "internet", "wifi", "sewa", "telepon", "pulsa", "token", "pln", "pdam", "kos", "kontrakan"]},
    {"name": "perlengkapan", "type": "pengeluaran", "icon": "🔧", "keywords": ["mesin jahit", "mesin obras", "gunting", "penggaris", "meja", "kursi", "pola", "cutting table", "benang gulung", "spool", "jarum"]},
    {"name": "packaging", "type": "pengeluaran", "icon": "📦", "keywords": ["plastik", "kardus", "selotip", "label", "hangtag", "stiker", "packing", "kemasan", "bubble wrap", "paper bag"]},
    {"name": "ongkir", "type": "pengeluaran", "icon": "🚚", "keywords": ["ongkir", "ongkos kirim", "kurir", "ekspedisi", "jne", "jnt", "sicepat", "anteraja", "grab", "gojek", "pengiriman", "kirim barang"]},
    {"name": "marketplace_fee", "type": "pengeluaran", "icon": "🏪", "keywords": ["fee shopee", "fee tokopedia", "fee tiktok", "komisi marketplace", "admin fee", "biaya platform", "layanan shopee", "layanan tokopedia"]},
    {"name": "marketing", "type": "pengeluaran", "icon": "📣", "keywords": ["iklan", "promosi", "endorse", "ads", "facebook ads", "instagram ads", "tiktok ads", "shopee ads", "tokopedia ads", "marketing", "boost"]},
    {"name": "gaji_karyawan", "type": "pengeluaran", "icon": "👷", "keywords": ["gaji", "upah karyawan", "thr", "bonus karyawan", "insentif", "karyawan", "pegawai", "buruh"]},
    {"name": "lainnya_biaya", "type": "pengeluaran", "icon": "📋", "keywords": ["lainnya", "lain", "dll", "administrasi", "bank", "transfer", "biaya lain"]},
    # Pemasukan (Revenue)
    {"name": "penjualan_online", "type": "pemasukan", "icon": "🛒", "keywords": ["shopee", "tokopedia", "tiktok shop", "lazada", "bukalapak", "blibli", "online", "marketplace", "olshop", "e-commerce"]},
    {"name": "penjualan_offline", "type": "pemasukan", "icon": "🏪", "keywords": ["toko", "offline", "langsung", "datang", "cash", "tunai", "warung", "kios"]},
    {"name": "pesanan_custom", "type": "pemasukan", "icon": "✂️", "keywords": ["seragam", "custom", "order", "pesanan", "jasa jahit", "jasa sablon", "almamater", "pramuka", "batik", "kerja", "korporat", "instansi", "sekolah"]},
    {"name": "DP_pesanan", "type": "pemasukan", "icon": "💰", "keywords": ["dp", "uang muka", "down payment", "tanda jadi", "booking", "pelunasan", "cicilan"]},
    {"name": "transfer_masuk", "type": "pemasukan", "icon": "📥", "keywords": ["transfer", "kiriman", "terima", "masuk", "mutasi masuk"]},
    {"name": "lainnya_masuk", "type": "pemasukan", "icon": "💵", "keywords": ["cashback", "refund", "bonus", "hadiah", "lainnya masuk"]},
]

# Product categories for konveksi
PRODUCT_CATEGORIES = [
    {"name": "Seragam SD", "icon": "👕"},
    {"name": "Seragam SMP", "icon": "👕"},
    {"name": "Seragam SMA", "icon": "👕"},
    {"name": "Seragam Pramuka", "icon": "🏕️"},
    {"name": "Seragam Batik", "icon": "🎭"},
    {"name": "Seragam Kerja", "icon": "👔"},
    {"name": "Almamater", "icon": "🎓"},
    {"name": "Jas", "icon": "🤵"},
    {"name": "Celana", "icon": "👖"},
    {"name": "Kaos", "icon": "👕"},
    {"name": "Kemeja", "icon": "👔"},
    {"name": "Topi", "icon": "🧢"},
    {"name": "Wearpack", "icon": "🦺"},
    {"name": "Lainnya", "icon": "📦"},
]
