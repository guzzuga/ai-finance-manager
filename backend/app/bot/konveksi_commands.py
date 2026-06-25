"""Konveksi bot commands — handle konveksi-specific Telegram commands."""
import logging
from datetime import date

from app.services.konveksi_service import KonveksiService
from app.bot.konveksi_formatter import KonveksiFormatter
from app.utils.date_helpers import get_today, get_start_of_month, get_end_of_month

logger = logging.getLogger(__name__)


async def handle_konveksi_command(command: str, chat_id: str, user_id: str, db, send_message) -> bool:
    """Handle konveksi-related commands. Returns True if command was handled."""

    # === STOK PRODUK ===
    if command == "/stok":
        products = KonveksiService.get_products(db, user_id=user_id)
        text = KonveksiFormatter.format_stock_report(products)
        await send_message(chat_id, text)
        return True

    # === STOK BAHAN BAKU ===
    if command == "/bahan":
        materials = KonveksiService.get_materials(db, user_id=user_id)
        text = KonveksiFormatter.format_material_list(materials)
        await send_message(chat_id, text)
        return True

    # === DAFTAR MARKETPLACE ===
    if command == "/marketplace":
        marketplaces = KonveksiService.get_marketplaces(db)
        text = KonveksiFormatter.format_marketplace_list(marketplaces)
        await send_message(chat_id, text)
        return True

    # === LAPORAN KONVEKSI ===
    if command in ("/konveksi", "/laba_konveksi"):
        today = get_today()
        start = get_start_of_month(today)
        end = get_end_of_month(today)
        report = KonveksiService.get_laporan_konveksi(db, user_id, start, end)
        text = KonveksiFormatter.format_laporan_konveksi(report, start, end)
        await send_message(chat_id, text)
        return True

    # === TAMBAH PRODUK ===
    if command.startswith("/tambah_produk"):
        parts = command.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await send_message(chat_id, (
                "📦 *Tambah Produk*\n\n"
                "Format: `/tambah_produk NAMA | HPP | HARGA JUAL | STOK`\n\n"
                "Contoh:\n"
                "• `/tambah_produk Kaos Polos L | 45000 | 85000 | 20`\n"
                "• `/tambah_produk Kemeja Flanel M | 65000 | 120000 | 10`"
            ))
            return True

        try:
            args = parts[1].strip().split("|")
            name = args[0].strip()
            hpp = int(args[1].strip()) if len(args) > 1 else 0
            price = int(args[2].strip()) if len(args) > 2 else 0
            stock = int(args[3].strip()) if len(args) > 3 else 0

            product = KonveksiService.create_product(db, {
                "name": name,
                "hpp": hpp,
                "price": price,
                "stock": stock,
                "user_id": user_id,
            })

            hpp_str = f"Rp {hpp:,.0f}".replace(",", ".")
            price_str = f"Rp {price:,.0f}".replace(",", ".")
            margin_str = f"Rp {price - hpp:,.0f}".replace(",", ".")

            await send_message(chat_id, (
                f"✅ *Produk Ditambahkan!*\n\n"
                f"📦 Nama: {name}\n"
                f"💰 HPP: {hpp_str}\n"
                f"🏷️ Harga Jual: {price_str}\n"
                f"📈 Margin: {margin_str}/pcs\n"
                f"📊 Stok: {stock} pcs"
            ))
        except Exception as e:
            logger.error("Error adding product: %s", e)
            await send_message(chat_id, "❌ Format salah! Contoh: `/tambah_produk Kaos L | 45000 | 85000 | 20`")
        return True

    # === TAMBAH BAHAN BAKU ===
    if command.startswith("/tambah_bahan"):
        parts = command.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await send_message(chat_id, (
                "🧵 *Tambah Bahan Baku*\n\n"
                "Format: `/tambah_bahan NAMA | UNIT | STOK | HARGA/UNIT`\n\n"
                "Contoh:\n"
                "• `/tambah_bahan Kain Katun | meter | 50 | 25000`\n"
                "• `/tambah_bahan Benang | roll | 10 | 15000`"
            ))
            return True

        try:
            args = parts[1].strip().split("|")
            name = args[0].strip()
            unit = args[1].strip() if len(args) > 1 else "meter"
            stock = float(args[2].strip()) if len(args) > 2 else 0
            price = int(args[3].strip()) if len(args) > 3 else 0

            material = KonveksiService.create_material(db, {
                "name": name,
                "unit": unit,
                "stock": stock,
                "price_per_unit": price,
                "user_id": user_id,
            })

            price_str = f"Rp {price:,.0f}".replace(",", ".")
            await send_message(chat_id, (
                f"✅ *Bahan Baku Ditambahkan!*\n\n"
                f"🧵 Nama: {name}\n"
                f"📊 Stok: {stock} {unit}\n"
                f"💰 Harga: {price_str}/{unit}"
            ))
        except Exception as e:
            logger.error("Error adding material: %s", e)
            await send_message(chat_id, "❌ Format salah! Contoh: `/tambah_bahan Kain Katun | meter | 50 | 25000`")
        return True

    return False
