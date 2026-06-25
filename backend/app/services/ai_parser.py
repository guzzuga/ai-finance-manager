"""AI Parser Service — uses MiMo API (OpenAI-compatible) to parse
natural language into structured transaction JSON.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Optional

import httpx

from app.config import MIMO_API_KEY, MIMO_BASE_URL, MIMO_MODEL, DEFAULT_CATEGORIES
from app.utils.currency import parse_indonesian_currency
from app.utils.date_helpers import get_today
from app.utils.categories import match_category

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_TEMPLATE = (
    "Kamu adalah parser keuangan. Ubah pesan user menjadi JSON. "
    "Hari ini tanggal {today_date}. "
    "Selalu jawab dengan JSON valid saja, tanpa markdown, tanpa penjelasan.\n\n"
    "Kategori pengeluaran: makanan, transport, rumah, belanja, pakaian, "
    "kesehatan, hiburan, pendidikan, komunikasi, lainnya.\n"
    "Kategori pemasukan: gaji, freelance, jualan, transfer_masuk, investasi, "
    "lainnya_masuk.\n\n"
    "Jika ada quantity dan unit (pcs, meter, roll, kg, liter, lusin, pack, dll), "
    "masukkan juga ke output.\n\n"
    'Format: {{"tanggal":"YYYY-MM-DD","jenis":"pemasukan/pengeluaran",'
    '"kategori":"nama_kategori","nominal":angka_tanpa_titik,"catatan":"string",'
    '"quantity":angka_atau_null,"unit":"nama_unit_atau_null"}}'
)

_PEMASUKAN_KW = re.compile(
    r'\b(gaji|gajian|salary|terima|masuk|pendapatan|freelance|jualan|jual|'
    r'dagang|komisi|dividen|bunga|cashback|refund|transfer\s*m|kiriman)\b',
    re.IGNORECASE,
)

_DATE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\b(?:tgl|tanggal)\s*(\d{1,2})\b', re.IGNORECASE), "day_only"),
    (re.compile(r'(\d{1,2})\s+(januari|februari|maret|april|mei|juni|juli|'
                r'agustus|september|oktober|november|desember)\b', re.IGNORECASE), "day_month_id"),
    (re.compile(r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', re.IGNORECASE), "dmy"),
    (re.compile(r'\b(kemarin|kemarin\s*lusa|lusa)\b', re.IGNORECASE), "relative"),
    (re.compile(r'\b(hari\s*ini)\b', re.IGNORECASE), "today"),
]

_MONTH_MAP_ID = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "september": 9, "oktober": 10, "november": 11, "desember": 12,
}

_AMOUNT_PATTERN = re.compile(
    r'(?:rp\.?\s*)?([\d]+[.,]?\d*)\s*(jt|juta|rb|ribu|m)?\b',
    re.IGNORECASE,
)

# Quantity + Unit pattern: "5 pcs", "10 meter", "2 roll", "3 kg", "1,5 liter"
_QUANTITY_UNIT_PATTERN = re.compile(
    r'\b(\d+(?:[.,]\d+)?)\s*(pcs|pc|bh|buah|meter|mtr|roll|rol|kg|kilogram|liter|ltr|lusin|pack|paket|set|unit|lembar|yard|kodi)\b',
    re.IGNORECASE,
)


class AIParser:
    """Parses natural-language finance messages into structured transaction dicts."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or MIMO_API_KEY
        self.base_url = (base_url or MIMO_BASE_URL).rstrip("/")
        self.model = model or MIMO_MODEL
        self.timeout = timeout

    async def parse(self, message: str, today_date: Optional[str] = None) -> dict:
        """Parse a natural-language message into a structured transaction dict."""
        if not message or not message.strip():
            return {"error": "Pesan kosong."}

        today_str = today_date or get_today().isoformat()

        # 1. Try regex/keyword fallback first
        fallback = self._fallback_parse(message, today_str)
        if fallback and not fallback.get("error"):
            if fallback.get("nominal", 0) > 0 and fallback.get("kategori"):
                logger.info("Fallback parser succeeded for: %s", message[:60])
                return fallback

        # 2. Call MiMo LLM
        try:
            result = await self._call_llm(message, today_str)
            if result and not result.get("error"):
                logger.info("LLM parser succeeded for: %s", message[:60])
                return result
        except Exception as exc:
            logger.warning("LLM parser failed: %s", exc)

        # 3. If LLM also failed but fallback had partial data, return it
        if fallback and not fallback.get("error"):
            logger.info("Returning partial fallback result for: %s", message[:60])
            return fallback

        return {
            "error": "Gagal memahami pesan. Coba format seperti: 'makan siang 25rb' atau 'gaji 5 juta'."
        }

    def _fallback_parse(self, message: str, today_str: str) -> Optional[dict]:
        """Best-effort regex/keyword extraction without any LLM call."""
        msg = message.strip()

        # Extract quantity+unit first so we can exclude that range from amount parsing
        quantity, unit, qty_range = self._extract_quantity_unit_with_range(msg)

        # Build exclude ranges: the quantity+unit match span
        exclude_ranges: list[tuple[int, int]] = []
        if qty_range is not None:
            exclude_ranges.append(qty_range)

        amount = self._extract_amount(msg, exclude_ranges=exclude_ranges)
        if amount is None or amount <= 0:
            return None

        jenis = "pemasukan" if _PEMASUKAN_KW.search(msg) else "pengeluaran"
        cat = match_category(msg, DEFAULT_CATEGORIES)
        kategori = cat["name"] if cat else ("lainnya_masuk" if jenis == "pemasukan" else "lainnya")
        tanggal = self._extract_date(msg, today_str)
        catatan = msg[:200]

        # Auto-calculate price per unit
        price_per_unit = None
        if quantity and unit and amount:
            price_per_unit = round(amount / quantity)

        return {
            "tanggal": tanggal,
            "jenis": jenis,
            "kategori": kategori,
            "nominal": amount,
            "catatan": catatan,
            "quantity": quantity,
            "unit": unit,
            "price_per_unit": price_per_unit,
        }

    async def _call_llm(self, message: str, today_str: str) -> Optional[dict]:
        """Call the MiMo API to parse the message via an LLM."""
        if not self.api_key:
            logger.error("MIMO_API_KEY not set — cannot call LLM.")
            return None

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(today_date=today_str)
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "temperature": 0.1,
            "max_tokens": 300,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()

        data = resp.json()

        try:
            content = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            logger.error("Unexpected LLM response structure: %s", exc)
            return None

        return self._parse_json_content(content)

    @staticmethod
    def _parse_json_content(content: str) -> Optional[dict]:
        """Extract and parse JSON from LLM response content."""
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n", 1)
            cleaned = lines[1] if len(lines) > 1 else lines[0]
            cleaned = re.sub(r'\n?```\s*$', '', cleaned).strip()

        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            m = re.search(r'\{[^{}]+\}', cleaned, re.DOTALL)
            if m:
                try:
                    result = json.loads(m.group())
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON from LLM response: %s", content[:200])
                    return None
            else:
                logger.error("No JSON object found in LLM response: %s", content[:200])
                return None

        expected = {"tanggal", "jenis", "kategori", "nominal", "catatan"}
        if not expected.issubset(result.keys()):
            logger.warning("LLM JSON missing keys. Got: %s", list(result.keys()))
            result.setdefault("tanggal", get_today().isoformat())
            result.setdefault("jenis", "pengeluaran")
            result.setdefault("kategori", "lainnya")
            result.setdefault("nominal", 0)
            result.setdefault("catatan", "")

        try:
            result["nominal"] = int(result["nominal"])
        except (ValueError, TypeError):
            result["nominal"] = 0

        # Handle quantity and unit (optional fields)
        result.setdefault("quantity", None)
        result.setdefault("unit", None)
        result.setdefault("price_per_unit", None)
        if result["quantity"] is not None:
            try:
                result["quantity"] = float(result["quantity"])
            except (ValueError, TypeError):
                result["quantity"] = None
                result["unit"] = None
                result["price_per_unit"] = None

        # Auto-calculate price_per_unit if quantity+unit+nominal present
        if result.get("quantity") and result.get("unit") and result.get("nominal"):
            if not result.get("price_per_unit"):
                result["price_per_unit"] = round(result["nominal"] / result["quantity"])
            else:
                try:
                    result["price_per_unit"] = int(result["price_per_unit"])
                except (ValueError, TypeError):
                    result["price_per_unit"] = round(result["nominal"] / result["quantity"])

        return result

    def _extract_amount(self, text: str, exclude_ranges: list[tuple[int, int]] | None = None) -> Optional[int]:
        """Extract the monetary amount from text using regex.

        When *exclude_ranges* is provided (list of (start, end) character ranges),
        any match that overlaps an excluded range is skipped.  This prevents
        quantity numbers (e.g. "5 roll") from being mistaken for the amount.
        """
        def _in_excluded(pos: int, length: int) -> bool:
            if not exclude_ranges:
                return False
            end = pos + length
            for rs, re_ in exclude_ranges:
                if pos < re_ and end > rs:
                    return True
            return False

        best = 0
        for m in _AMOUNT_PATTERN.finditer(text):
            if _in_excluded(m.start(), len(m.group())):
                continue
            num_str = m.group(1)
            mult = (m.group(2) or "").lower()
            val = parse_indonesian_currency(f"{num_str} {mult}".strip())
            if val > best:
                best = val

        if best > 0:
            return best

        # Fallback: any standalone number (excluding quantity ranges)
        for m in re.finditer(r'\b\d[\d.,]*\b', text):
            if _in_excluded(m.start(), len(m.group())):
                continue
            val = parse_indonesian_currency(m.group())
            if val > best:
                best = val

        return best if best > 0 else None

    def _extract_date(self, text: str, today_str: str) -> str:
        """Extract a date from text; defaults to today_str."""
        today = date.fromisoformat(today_str)

        for pattern, kind in _DATE_PATTERNS:
            m = pattern.search(text)
            if not m:
                continue

            if kind == "today":
                return today_str

            if kind == "relative":
                word = m.group(1).lower().strip()
                if "lusa" in word:
                    from datetime import timedelta
                    return (today + timedelta(days=2)).isoformat()
                elif "kemarin" in word:
                    from datetime import timedelta
                    return (today - timedelta(days=1)).isoformat()

            if kind == "day_only":
                day = int(m.group(1))
                if 1 <= day <= 31:
                    try:
                        return date(today.year, today.month, day).isoformat()
                    except ValueError:
                        pass

            if kind == "day_month_id":
                day = int(m.group(1))
                month_name = m.group(2).lower()
                month = _MONTH_MAP_ID.get(month_name)
                if month and 1 <= day <= 31:
                    try:
                        return date(today.year, month, day).isoformat()
                    except ValueError:
                        pass

            if kind == "dmy":
                day = int(m.group(1))
                month = int(m.group(2))
                year_str = m.group(3)
                year = int(year_str) if year_str else today.year
                if year < 100:
                    year += 2000
                if 1 <= month <= 12 and 1 <= day <= 31:
                    try:
                        return date(year, month, day).isoformat()
                    except ValueError:
                        pass

        return today_str

    def _extract_quantity_unit(self, text: str) -> tuple[Optional[float], Optional[str]]:
        """Extract quantity and unit from text.

        Examples:
            "jual kaos polo 5 pcs 250 ribu" → (5.0, "pcs")
            "beli kain 5 meter 250rb" → (5.0, "meter")
            "beli kain 1 roll 1,2 juta" → (1.0, "roll")
            "3,5 kg beras 50rb" → (3.5, "kg")
        """
        qty, unit, _ = self._extract_quantity_unit_with_range(text)
        return qty, unit

    def _extract_quantity_unit_with_range(
        self, text: str
    ) -> tuple[Optional[float], Optional[str], Optional[tuple[int, int]]]:
        """Extract quantity, unit, and the character range of the match.

        Returns (quantity, unit, (start, end)) or (None, None, None).
        """
        m = _QUANTITY_UNIT_PATTERN.search(text)
        if m:
            qty_str = m.group(1).replace(',', '.')
            try:
                quantity = float(qty_str)
            except ValueError:
                return None, None, None
            unit = m.group(2).lower()
            # Normalize units
            unit_map = {
                'pc': 'pcs', 'bh': 'pcs', 'buah': 'pcs',
                'mtr': 'meter', 'm': 'meter',
                'rol': 'roll',
                'kilogram': 'kg',
                'ltr': 'liter',
            }
            unit = unit_map.get(unit, unit)
            return quantity, unit, (m.start(), m.end())
        return None, None, None
