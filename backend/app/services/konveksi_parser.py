"""Konveksi message parser — detects sale, production, and material purchase messages."""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Pattern: "jual kaos L 3pcs di shopee 85rb"
_SALE_PATTERN = re.compile(
    r'\b(jual|terjual|sold|order|pesanan)\b'
    r'.*?'  # product name
    r'\b(\d+(?:[.,]\d+)?)\s*(pcs|pc|bh|buah|lusin|pack)\b'  # quantity
    r'.*?'
    r'\b(di|di marketplace|via)\s+(\w+)\b'  # marketplace
    r'.*?'
    r'(?:rp\.?\s*)?([\d]+[.,]?\d*)\s*(jt|juta|rb|ribu|m)?\b',  # price
    re.IGNORECASE | re.DOTALL,
)

# Pattern: "produksi kaos L 10pcs"
_PRODUCTION_PATTERN = re.compile(
    r'\b(produksi|produksi|buat|jahit|cetak)\b'
    r'.*?'  # product name
    r'\b(\d+(?:[.,]\d+)?)\s*(pcs|pc|bh|buah|lusin|pack)\b',  # quantity
    re.IGNORECASE | re.DOTALL,
)

# Pattern: "beli kain 10 meter 250rb"
_MATERIAL_PURCHASE_PATTERN = re.compile(
    r'\b(beli|belanja|pesan|order)\b'
    r'.*?'
    r'\b(kain|benang|kancing|resleting|label|benang jahit|kain katun|kain drill)\b'
    r'.*?'
    r'\b(\d+(?:[.,]\d+)?)\s*(meter|mtr|roll|rol|kg|yard|lusin|pack)\b',  # quantity + unit
    re.IGNORECASE | re.DOTALL,
)

# Marketplace name mapping
_MARKETPLACE_MAP = {
    "shopee": "Shopee",
    "shoope": "Shopee",
    "tokped": "Tokopedia",
    "tokopedia": "Tokopedia",
    "lazada": "Lazada",
    "bukalapak": "Bukalapak",
    "bl": "Bukalapak",
    "tiktok": "TikTok Shop",
    "tiktokshop": "TikTok Shop",
    "tt": "TikTok Shop",
    "offline": "Offline/Toko",
    "toko": "Offline/Toko",
    "langsung": "Offline/Toko",
}


def parse_indonesian_amount(text: str) -> int:
    """Parse Indonesian currency text to integer.
    
    Handles:
        '1,2 juta' -> 1200000 (comma = decimal)
        '1.5 juta' -> 1500000 (dot = decimal before multiplier)
        '150.000'  -> 150000  (dot = thousands separator, no multiplier)
        '85rb'     -> 85000
    """
    text = text.strip().lower()
    mult = 1
    
    # Check multiplier FIRST, before stripping separators
    for suffix, m in [("jt", 1_000_000), ("juta", 1_000_000), ("rb", 1_000), ("ribu", 1_000), ("m", 1_000_000)]:
        if text.endswith(suffix):
            num_part = text[:-len(suffix)].strip()
            # In the number part, comma = decimal separator (Indonesian style)
            num_part = num_part.replace(",", ".")
            # If there are multiple dots, keep only the last as decimal
            parts = num_part.split(".")
            if len(parts) > 2:
                num_part = "".join(parts[:-1]) + "." + parts[-1]
            elif len(parts) == 2 and len(parts[1]) == 3:
                # "150.000" style with 3-digit decimal = thousands separator
                num_part = parts[0] + parts[1]
            try:
                return int(float(num_part) * m)
            except (ValueError, TypeError):
                return 0
    
    # No multiplier — treat as raw number
    # Remove thousands separators (dots with 3 digits after)
    text_clean = text.replace(",", "")
    # Handle "150.000" -> "150000" (thousands separator)
    parts = text_clean.split(".")
    if len(parts) == 2 and len(parts[1]) == 3:
        text_clean = parts[0] + parts[1]
    else:
        text_clean = text_clean.replace(".", "")
    
    try:
        return int(text_clean)
    except (ValueError, TypeError):
        return 0


def detect_sale_message(message: str) -> Optional[dict]:
    """Detect if message is a sale record.
    
    Examples:
        "jual kaos L 3pcs di shopee 85rb"
        "terjual kemeja flanel 2pcs di tokped 120rb"
        "order kaos polos 5 pcs di shopee 85000"
    """
    msg = message.strip()

    # Check for sale keywords
    sale_keywords = ["jual", "terjual", "sold", "pesanan"]
    has_sale_kw = any(kw in msg.lower() for kw in sale_keywords)
    if not has_sale_kw:
        return None

    # Extract quantity + unit
    qty_match = re.search(r'\b(\d+(?:[.,]\d+)?)\s*(pcs|pc|bh|buah|lusin|pack)\b', msg, re.IGNORECASE)
    if not qty_match:
        return None

    quantity = int(float(qty_match.group(1).replace(",", ".")))
    unit = qty_match.group(2).lower()

    # Extract marketplace
    marketplace_name = None
    mp_match = re.search(r'\b(di|via)\s+(\w+)\b', msg, re.IGNORECASE)
    if mp_match:
        mp_key = mp_match.group(2).lower()
        marketplace_name = _MARKETPLACE_MAP.get(mp_key, mp_match.group(2))

    # Extract price (look for amount after quantity)
    price = 0
    # Try to find price after the marketplace mention
    price_section = msg[qty_match.end():]
    price_match = re.search(r'(?:rp\.?\s*)?([\d]+[.,]?\d*)\s*(jt|juta|rb|ribu|m)?\b', price_section, re.IGNORECASE)
    if price_match:
        price = parse_indonesian_amount(f"{price_match.group(1)} {price_match.group(2) or ''}")

    # Extract product name (between sale keyword and quantity)
    product_section = msg[:qty_match.start()]
    # Remove sale keywords
    for kw in sale_keywords:
        product_section = re.sub(rf'\b{kw}\b', '', product_section, flags=re.IGNORECASE)
    product_name = product_section.strip()
    # Clean up common words
    product_name = re.sub(r'\b(di|via|harga|rp|seharga)\b.*', '', product_name, flags=re.IGNORECASE).strip()

    if not product_name or quantity <= 0:
        return None

    return {
        "type": "sale",
        "product_name": product_name,
        "quantity": quantity,
        "unit": unit,
        "marketplace_name": marketplace_name,
        "total_price": price,  # This is the TOTAL price, not per-unit
        "raw_message": message,
    }


def detect_production_message(message: str) -> Optional[dict]:
    """Detect if message is a production record.
    
    Examples:
        "produksi kaos L 10pcs"
        "jahit kemeja flanel 5 pcs"
        "buat celana chino 20 pcs"
    """
    msg = message.strip()

    prod_keywords = ["produksi", "jahit", "cetak", "konveksi"]
    has_prod_kw = any(kw in msg.lower() for kw in prod_keywords)
    if not has_prod_kw:
        return None

    # Extract quantity + unit
    qty_match = re.search(r'\b(\d+(?:[.,]\d+)?)\s*(pcs|pc|bh|buah|lusin|pack)\b', msg, re.IGNORECASE)
    if not qty_match:
        return None

    quantity = int(float(qty_match.group(1).replace(",", ".")))

    # Extract product name (between prod keyword and quantity)
    product_section = msg[:qty_match.start()]
    for kw in prod_keywords:
        product_section = re.sub(rf'\b{kw}\b', '', product_section, flags=re.IGNORECASE)
    product_name = product_section.strip()

    if not product_name or quantity <= 0:
        return None

    return {
        "type": "production",
        "product_name": product_name,
        "quantity": quantity,
        "raw_message": message,
    }


def detect_material_purchase_message(message: str) -> Optional[dict]:
    """Detect if message is a material purchase.
    
    Examples:
        "beli kain katun 10 meter 250rb"
        "beli benang 5 roll 75rb"
        "pesan kain drill 20 meter 500rb"
    """
    msg = message.strip()

    buy_keywords = ["beli", "belanja", "pesan", "order"]
    has_buy_kw = any(kw in msg.lower() for kw in buy_keywords)
    if not has_buy_kw:
        return None

    # Check for material keywords
    material_keywords = ["kain", "benang", "kancing", "resleting", "label"]
    material_match = re.search(r'\b(' + '|'.join(material_keywords) + r')\b', msg, re.IGNORECASE)
    if not material_match:
        return None

    # Extract quantity + unit
    qty_match = re.search(r'\b(\d+(?:[.,]\d+)?)\s*(meter|mtr|roll|rol|kg|yard|lusin|pack)\b', msg, re.IGNORECASE)
    if not qty_match:
        return None

    quantity = float(qty_match.group(1).replace(",", "."))
    unit = qty_match.group(2).lower()
    unit_map = {'mtr': 'meter', 'rol': 'roll'}
    unit = unit_map.get(unit, unit)

    # Extract total price
    price = 0
    price_section = msg[qty_match.end():]
    price_match = re.search(r'(?:rp\.?\s*)?([\d]+[.,]?\d*)\s*(jt|juta|rb|ribu|m)?\b', price_section, re.IGNORECASE)
    if price_match:
        price = parse_indonesian_amount(f"{price_match.group(1)} {price_match.group(2) or ''}")

    # Extract material name
    material_section = msg[:qty_match.start()]
    for kw in buy_keywords:
        material_section = re.sub(rf'\b{kw}\b', '', material_section, flags=re.IGNORECASE)
    material_name = material_section.strip()

    if not material_name or quantity <= 0:
        return None

    return {
        "type": "material_purchase",
        "material_name": material_name,
        "quantity": quantity,
        "unit": unit,
        "total_price": price,
        "price_per_unit": int(price / quantity) if quantity > 0 and price > 0 else 0,
        "raw_message": message,
    }
