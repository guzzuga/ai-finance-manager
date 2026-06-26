"""Telegram Polling Bot — Guzsan Finance AI

Long-running polling bot that processes messages and commands.
Integrates with:
- AI Parser (MiMo API) for natural language processing
- Google Sheets (Maton API) for auto-sync
- SQLite database for local storage

Commands synced with dashboard:
  /start, /help, /bantuan  — Help
  /ringkasan               — Ringkasan bulan ini
  /hariini                 — Pengeluaran hari ini
  /mingguini, /mingguan    — Laporan mingguan (Senin–hari ini)
  /bulanini                — Rincian bulan ini
  /riwayat                 — 10 transaksi terakhir
  /kategori                — Breakdown per kategori
  /profit                  — Laporan keuntungan bulanan
  /cashflow                — Arus kas 30 hari terakhir
  /export                  — Download Excel (coming soon)
  /insight                 — AI insight (coming soon)
  /reset                   — Reset data (coming soon)
"""
import logging
import sys
import os
import json
from datetime import date, datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config import TELEGRAM_BOT_TOKEN
from app.database.connection import SessionLocal, init_db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.ai_parser import AIParser
from app.services.transaction_service import TransactionService
from app.services.report_service import ReportService
from app.services.konveksi_service import KonveksiService
from app.services.konveksi_parser import detect_sale_message, detect_production_message, detect_material_purchase_message
from app.services import google_sheets_service
from app.bot.response_formatter import ResponseFormatter
from app.bot.konveksi_formatter import KonveksiFormatter
from app.bot.konveksi_commands import handle_konveksi_command
from app.utils.date_helpers import get_today, get_start_of_month, get_end_of_month, get_start_of_week
from app.config import DEFAULT_CATEGORIES

import asyncio
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
parser = AIParser()


def seed_categories(db):
    """Seed default categories if table is empty."""
    existing = db.query(Category).count()
    if existing > 0:
        return

    logger.info("Seeding %d default categories...", len(DEFAULT_CATEGORIES))
    import uuid
    for cat_cfg in DEFAULT_CATEGORIES:
        kw = cat_cfg.get("keywords", [])
        cat = Category(
            id=str(uuid.uuid4()),
            name=cat_cfg["name"],
            type=cat_cfg["type"],
            icon=cat_cfg.get("icon", "📦"),
            keywords=json.dumps(kw) if kw else None,
            user_id=None,
        )
        db.add(cat)
    db.commit()
    logger.info("Default categories seeded.")


async def send_message(chat_id: str, text: str, reply_markup: dict = None) -> None:
    """Send a text message back to a Telegram chat."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not configured")
        return

    url = f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                # If Markdown parsing fails, retry without parse_mode
                logger.warning("Telegram sendMessage failed (Markdown), retrying plain text")
                payload.pop("parse_mode", None)
                resp2 = await client.post(url, json=payload)
                if resp2.status_code != 200:
                    logger.warning("Telegram sendMessage failed again: %s", resp2.text[:200])
    except Exception as exc:
        logger.error("Failed to send Telegram message: %s", exc)


async def set_bot_commands() -> None:
    """Register bot commands with Telegram (shows in / menu)."""
    commands = [
        {"command": "start", "description": "🏠 Mulai bot"},
        {"command": "catat_pemasukan", "description": "➕ Catat pemasukan"},
        {"command": "catat_pengeluaran", "description": "➖ Catat pengeluaran"},
        {"command": "hariini", "description": "📅 Pengeluaran hari ini"},
        {"command": "mingguini", "description": "📆 Laporan mingguan"},
        {"command": "bulanini", "description": "📊 Rincian bulan ini"},
        {"command": "ringkasan", "description": "📋 Ringkasan bulan ini"},
        {"command": "cashflow", "description": "💰 Arus kas 30 hari"},
        {"command": "riwayat", "description": "📝 10 transaksi terakhir"},
        {"command": "kategori", "description": "🏷️ Breakdown per kategori"},
        {"command": "profit", "description": "📈 Laporan keuntungan"},
        {"command": "konveksi", "description": "🏭 Laporan konveksi"},
        {"command": "stok", "description": "📦 Stok produk"},
        {"command": "bahan", "description": "🧵 Stok bahan baku"},
        {"command": "marketplace", "description": "🛒 Daftar marketplace"},
        {"command": "tambah_produk", "description": "➕ Tambah produk baru"},
        {"command": "tambah_bahan", "description": "➕ Tambah bahan baku"},
        {"command": "adduser", "description": "👤 Tambah user baru"},
        {"command": "reset", "description": "🗑️ Reset semua data"},
        {"command": "bantuan", "description": "❓ Bantuan"},
    ]
    url = f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/setMyCommands"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json={"commands": commands})
            if resp.status_code == 200:
                logger.info("✅ Bot commands registered")
            else:
                logger.warning("setMyCommands failed: %s", resp.text[:200])
    except Exception as exc:
        logger.error("Failed to set bot commands: %s", exc)


def get_reply_keyboard() -> dict:
    """Get persistent reply keyboard (shows at bottom of chat, next to attach)."""
    return {
        "keyboard": [
            [
                {"text": "➕ Catat Pemasukan"},
                {"text": "➖ Catat Pengeluaran"},
            ],
            [
                {"text": "📅 Hari Ini"},
                {"text": "📆 Minggu Ini"},
                {"text": "💰 Cashflow"},
            ],
            [
                {"text": "📝 Riwayat"},
                {"text": "🏷️ Kategori"},
                {"text": "📊 Bulan Ini"},
            ],
            [
                {"text": "📈 Profit"},
                {"text": "📋 Ringkasan"},
                {"text": "🏭 Konveksi"},
            ],
            [
                {"text": "📦 Stok"},
                {"text": "🧵 Bahan"},
                {"text": "🛒 Marketplace"},
            ],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def get_main_menu_keyboard() -> dict:
    """Get inline keyboard for main menu."""
    return {
        "inline_keyboard": [
            [
                {"text": "📅 Hari Ini", "callback_data": "/hariini"},
                {"text": "📆 Minggu Ini", "callback_data": "/mingguini"},
            ],
            [
                {"text": "📊 Bulan Ini", "callback_data": "/bulanini"},
                {"text": "💰 Cashflow", "callback_data": "/cashflow"},
            ],
            [
                {"text": "📝 Riwayat", "callback_data": "/riwayat"},
                {"text": "🏷️ Kategori", "callback_data": "/kategori"},
            ],
            [
                {"text": "📈 Profit", "callback_data": "/profit"},
                {"text": "📋 Ringkasan", "callback_data": "/ringkasan"},
            ],
            [
                {"text": "❓ Bantuan", "callback_data": "/bantuan"},
            ],
        ]
    }


async def send_document(chat_id: str, file_path: str, caption: str = "") -> None:
    """Send a document to a Telegram chat."""
    if not TELEGRAM_BOT_TOKEN:
        return

    url = f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(file_path, "rb") as f:
                files = {"document": (os.path.basename(file_path), f)}
                data = {"chat_id": chat_id, "caption": caption}
                resp = await client.post(url, data=data, files=files)
                if resp.status_code != 200:
                    logger.warning("Telegram sendDocument failed: %s", resp.text[:200])
    except Exception as exc:
        logger.error("Failed to send document: %s", exc)


async def handle_command(command: str, chat_id: str, user_id: str, db, full_text: str = "") -> None:
    """Handle bot commands and send the reply."""
    today = get_today()

    # === HELP ===
    if command in ("/start", "/help", "/bantuan"):
        await send_message(chat_id, ResponseFormatter.format_help(), reply_markup=get_reply_keyboard())
        return

    # === CATAT PEMASUKAN ===
    if command == "/catat_pemasukan":
        await send_message(chat_id, "➕ *Catat Pemasukan*\n\nKirim pesan dengan format:\n• `jual seragam SD 20 pcs 85rb`\n• `order almamater 50 pcs 120rb`\n• `DP pesanan 500rb`\n\nAtau ketik langsung nominalnya:")
        return

    # === CATAT PENGELUARAN ===
    if command == "/catat_pengeluaran":
        await send_message(chat_id, "➖ *Catat Pengeluaran*\n\nKirim pesan dengan format:\n• `beli kain tropical 10 meter 2,1 juta`\n• `bayar jahit 50 pcs 750rb`\n• `ongkir JNE 35rb`\n\nAtau ketik langsung nominalnya:")
        return

    # === RINGKASAN BULAN INI ===
    if command in ("/total", "/ringkasan"):
        start = get_start_of_month(today)
        end = get_end_of_month(today)
        summary = ReportService.get_summary(db, user_id, start, end)
        summary["start_date"] = start
        summary["end_date"] = end
        await send_message(chat_id, ResponseFormatter.format_summary(summary))
        return

    # === HARI INI ===
    if command == "/hariini":
        summary = ReportService.get_summary(db, user_id, today, today)
        summary["start_date"] = today
        summary["end_date"] = today
        transactions = ReportService.get_recent_transactions(db, user_id, limit=50)
        today_transactions = [t for t in transactions if str(t.date) == str(today)]
        await send_message(chat_id, ResponseFormatter.format_today_report(summary, today_transactions))
        return

    # === LAPORAN MINGGUAN ===
    if command in ("/mingguini", "/mingguan"):
        start = get_start_of_week(today)
        end = today
        summary = ReportService.get_summary(db, user_id, start, end)
        summary["start_date"] = start
        summary["end_date"] = end
        daily = ReportService.get_daily_totals(db, user_id, start, end)
        breakdown = ReportService.get_category_breakdown(db, user_id, start, end)
        await send_message(chat_id, ResponseFormatter.format_weekly_report(summary, daily, breakdown))
        return

    # === RINCIAN BULAN INI ===
    if command == "/bulanini":
        start = get_start_of_month(today)
        end = get_end_of_month(today)
        summary = ReportService.get_summary(db, user_id, start, end)
        summary["start_date"] = start
        summary["end_date"] = end
        await send_message(chat_id, ResponseFormatter.format_summary(summary))
        return

    # === RIWAYAT TRANSAKSI ===
    if command == "/riwayat":
        transactions = ReportService.get_recent_transactions(db, user_id, limit=10)
        text = ResponseFormatter.format_transaction_list(transactions)
        await send_message(chat_id, text)
        return

    # === BREAKDOWN KATEGORI ===
    if command == "/kategori":
        start = get_start_of_month(today)
        end = get_end_of_month(today)
        breakdown = ReportService.get_category_breakdown(db, user_id, start, end)
        await send_message(chat_id, ResponseFormatter.format_category_breakdown(breakdown))
        return

    # === EXPORT EXCEL ===
    if command == "/export":
        await send_message(chat_id, "📥 Sedang menyiapkan file Excel...")
        # TODO: Implement Excel export
        await send_message(chat_id, "Fitur export Excel akan segera tersedia.")
        return

    # === AI INSIGHT ===
    if command == "/insight":
        await send_message(chat_id, "🤖 Sedang menganalisis data keuangan Anda...")
        # TODO: Implement AI insight
        await send_message(chat_id, "Fitur AI insight akan segera tersedia.")
        return

    # === LAPORAN KEUNTUNGAN ===
    if command == "/profit":
        start = get_start_of_month(today)
        end = get_end_of_month(today)
        summary = ReportService.get_summary(db, user_id, start, end)
        summary["start_date"] = start
        summary["end_date"] = end
        profit_text = f"""📊 *Laporan Keuntungan Bulan Ini*
📅 {start} s/d {end}

💰 Pemasukan: Rp {summary['pemasukan']:,.0f}
💸 Pengeluaran: Rp {summary['pengeluaran']:,.0f}
📈 Keuntungan: Rp {summary['saldo']:,.0f}

Keuntungan = Pemasukan - Pengeluaran"""
        await send_message(chat_id, profit_text.replace(",", "."))
        return

    # === ARUS KAS 30 HARI (synced with dashboard) ===
    if command == "/cashflow":
        from datetime import timedelta
        start = today - timedelta(days=30)
        daily = ReportService.get_daily_totals(db, user_id, start, today)
        await send_message(chat_id, ResponseFormatter.format_cashflow_report(daily))
        return

    # === RESET DATA ===
    if command == "/reset":
        await send_message(chat_id, "⚠️ *Reset Data*\n\nKirim `/reset_confirm` untuk menghapus SEMUA transaksi Anda.\n\n📋 Data akan dihapus dari:\n• Database lokal\n• Google Sheets\n• Dashboard\n\n⛔ _Tindakan ini tidak bisa dibatalkan!_")
        return

    if command == "/reset_confirm":
        try:
            count = TransactionService.reset_user_data(db, user_id)
            await send_message(chat_id, f"✅ Data berhasil di-reset!\n\n🗑️ {count} transaksi dihapus\n📊 Google Sheets dikosongkan\n🖥️ Dashboard ter-refresh\n\nSiap mencatat dari awal!")
        except Exception as exc:
            logger.error("Reset failed: %s", exc)
            await send_message(chat_id, "❌ Gagal reset data.")
        return

    # === TAMBAH USER ===
    if command.startswith("/adduser"):
        parts = command.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await send_message(chat_id, "👤 *Tambah User*\n\nFormat: `/adduser TELEGRAM_ID NAMA`\n\nContoh:\n• `/adduser 123456789 Budi`\n• `/adduser 987654321 Siti`\n\nCek Telegram ID: kirim `/start` ke @userinfobot")
            return
        args = parts[1].strip().split(maxsplit=1)
        if len(args) < 2:
            await send_message(chat_id, "❌ Format salah!\n\nFormat: `/adduser TELEGRAM_ID NAMA`\nContoh: `/adduser 123456789 Budi`")
            return
        telegram_id = args[0].strip()
        name = args[1].strip()
        if not telegram_id.isdigit():
            await send_message(chat_id, "❌ Telegram ID harus angka!\n\nContoh: `/adduser 123456789 Budi`")
            return
        try:
            user, username, password = TransactionService.add_user(db, name, platform_id=telegram_id)
            await send_message(chat_id, f"""✅ User berhasil ditambahkan!

👤 *{name}*
🆔 Telegram ID: `{telegram_id}`

🔐 *Login Dashboard:*
• Username: `{username}`
• Password: `{password}`
• URL: http://your-server:8000

📊 Data dan Google Sheet terpisah dari akun lain.""")
        except Exception as exc:
            logger.error("Add user failed: %s", exc)
            await send_message(chat_id, "❌ Gagal menambahkan user.")
        return

    # === KONVEKSI COMMANDS ===
    konveksi_handled = await handle_konveksi_command(command, chat_id, user_id, db, send_message, original_text=full_text)
    if konveksi_handled:
        return

    # Unknown command
    await send_message(chat_id, "Perintah tidak dikenali. Ketik /bantuan untuk melihat daftar perintah.")


async def process_message(message: dict, db) -> None:
    """Process a single Telegram message."""
    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    text = (message.get("text") or "").strip()
    from_user = message.get("from", {})

    # Skip bot's own messages to prevent infinite loops
    if from_user.get("is_bot"):
        return

    user_name = from_user.get("first_name", "")
    telegram_user_id = str(from_user.get("id", ""))

    if not chat_id or not text:
        return

    try:
        # Get or create user
        user = TransactionService.get_or_create_user(
            db,
            platform="telegram",
            platform_id=telegram_user_id or chat_id,
            name=user_name,
        )

        # Map reply keyboard button text to commands
        button_to_command = {
            "➕ catat pemasukan": "/catat_pemasukan",
            "➖ catat pengeluaran": "/catat_pengeluaran",
            "📅 hari ini": "/hariini",
            "📆 minggu ini": "/mingguini",
            "💰 cashflow": "/cashflow",
            "📝 riwayat": "/riwayat",
            "🏷️ kategori": "/kategori",
            "📊 bulan ini": "/bulanini",
            "📈 profit": "/profit",
            "📋 ringkasan": "/ringkasan",
            "🏭 konveksi": "/konveksi",
            "📦 stok": "/stok",
            "🧵 bahan": "/bahan",
            "🛒 marketplace": "/marketplace",
        }

        # Check if it's a reply keyboard button
        text_lower = text.lower().strip()
        if text_lower in button_to_command:
            command = button_to_command[text_lower]
            await handle_command(command, chat_id, user.id, db, full_text=text)
            return

        # Check if it's a /command
        if text.startswith("/"):
            command = text.split("@")[0].split()[0].lower()
            await handle_command(command, chat_id, user.id, db, full_text=text)
            return

        # Regular message → try konveksi detection first, then parse as transaction
        today_str = str(get_today())

        # 1. Try sale detection
        sale_data = detect_sale_message(text)
        if sale_data:
            try:
                total_price = sale_data.get("total_price", 0)
                quantity = sale_data.get("quantity", 1)
                price_per_unit = round(total_price / quantity) if quantity > 0 and total_price > 0 else 0

                # Find or create product
                product = KonveksiService.get_product_by_name(db, sale_data["product_name"])
                if not product:
                    product = KonveksiService.create_product(db, {
                        "name": sale_data["product_name"],
                        "price": price_per_unit,
                        "user_id": user.id,
                    })

                # Find marketplace
                marketplace = None
                if sale_data.get("marketplace_name"):
                    marketplace = KonveksiService.get_marketplace_by_name(db, sale_data["marketplace_name"])
                if not marketplace:
                    marketplace = KonveksiService.get_marketplace_by_name(db, "Offline")

                if marketplace:
                    sale = KonveksiService.create_sale(db, {
                        "user_id": user.id,
                        "product_id": product.id,
                        "marketplace_id": marketplace.id,
                        "date": today_str,
                        "quantity": quantity,
                        "price_per_unit": price_per_unit,
                        "hpp_per_unit": product.hpp,
                        "raw_message": text,
                        "source": "telegram",
                    })
                    reply = KonveksiFormatter.format_sale_reply(sale)
                    await send_message(chat_id, reply)
                    return
            except Exception as e:
                logger.error("Sale detection error: %s", e)
                # Fall through to regular parsing

        # 2. Try production detection
        prod_data = detect_production_message(text)
        if prod_data:
            try:
                product = KonveksiService.get_product_by_name(db, prod_data["product_name"])
                if not product:
                    product = KonveksiService.create_product(db, {
                        "name": prod_data["product_name"],
                        "user_id": user.id,
                    })

                production = KonveksiService.create_production(db, {
                    "user_id": user.id,
                    "product_id": product.id,
                    "date": today_str,
                    "quantity": prod_data["quantity"],
                    "cost_per_unit": product.hpp,
                    "raw_message": text,
                    "source": "telegram",
                })
                reply = KonveksiFormatter.format_production_reply(production)
                await send_message(chat_id, reply)
                return
            except Exception as e:
                logger.error("Production detection error: %s", e)

        # 3. Try material purchase detection
        mat_data = detect_material_purchase_message(text)
        if mat_data:
            try:
                material = KonveksiService.get_material_by_name(db, mat_data["material_name"])
                if material:
                    KonveksiService.update_material_stock(db, material.id, mat_data["quantity"])
                    price_str = f"Rp {mat_data['total_price']:,.0f}".replace(",", ".")
                    # Sync to Google Sheets
                    try:
                        google_sheets_service.append_bahan_baku(
                            tanggal=str(get_today()),
                            nama=material.name,
                            unit=mat_data["unit"],
                            qty=mat_data["quantity"],
                            harga_per_unit=mat_data.get("price_per_unit", 0),
                            total=mat_data["total_price"],
                        )
                    except Exception as e:
                        logger.warning("Failed to sync bahan baku to Sheets: %s", e)
                    await send_message(chat_id, (
                        f"✅ *Bahan Baku Ditambahkan!*\n\n"
                        f"🧵 {material.name}: +{mat_data['quantity']} {mat_data['unit']}\n"
                        f"💰 Total: {price_str}\n"
                        f"📊 Stok sekarang: {material.stock} {material.unit}"
                    ))
                    return
                else:
                    # Create new material
                    material = KonveksiService.create_material(db, {
                        "name": mat_data["material_name"],
                        "unit": mat_data["unit"],
                        "stock": mat_data["quantity"],
                        "price_per_unit": mat_data.get("price_per_unit", 0),
                        "user_id": user.id,
                    })
                    price_str = f"Rp {mat_data['total_price']:,.0f}".replace(",", ".")
                    # Create pengeluaran transaction for material purchase
                    total_price = int(mat_data["total_price"])
                    if total_price > 0:
                        from app.services.transaction_service import TransactionService
                        TransactionService.create_transaction(
                            db,
                            user_id=user.id,
                            parsed={
                                "type": "pengeluaran",
                                "amount": total_price,
                                "category": "bahan_baku",
                                "note": f"Beli {material.name} {mat_data['quantity']} {mat_data['unit']}",
                                "date": str(get_today()),
                                "quantity": mat_data["quantity"],
                                "unit": mat_data["unit"],
                            },
                            raw_message=text,
                            source="telegram",
                        )
                    # Sync to Google Sheets
                    try:
                        google_sheets_service.append_bahan_baku(
                            tanggal=str(get_today()),
                            nama=material.name,
                            unit=mat_data["unit"],
                            qty=mat_data["quantity"],
                            harga_per_unit=mat_data.get("price_per_unit", 0),
                            total=mat_data["total_price"],
                        )
                        # Also sync to Pengeluaran Sheet1
                        if total_price > 0:
                            google_sheets_service.append_transaction(
                                tanggal=str(get_today()),
                                jenis="pengeluaran",
                                kategori="bahan_baku",
                                nominal=total_price,
                                catatan=f"Beli {material.name} {mat_data['quantity']} {mat_data['unit']}",
                                sumber="telegram",
                                quantity=mat_data["quantity"],
                                unit=mat_data["unit"],
                                price_per_unit=mat_data.get("price_per_unit", 0),
                            )
                    except Exception as e:
                        logger.warning("Failed to sync bahan baku to Sheets: %s", e)
                    await send_message(chat_id, (
                        f"✅ *Bahan Baku Baru Ditambahkan!*\n\n"
                        f"🧵 {material.name}\n"
                        f"📊 Stok: {mat_data['quantity']} {mat_data['unit']}\n"
                        f"💰 Harga: {price_str}"
                    ))
                    return
            except Exception as e:
                logger.error("Material detection error: %s", e)

        # 4. Fall through to regular transaction parsing
        parsed = await parser.parse(text)

        if parsed.get("error"):
            await send_message(chat_id, f"❌ {parsed['error']}")
            return

        # Map AI parser output → TransactionService expected keys
        mapped = {
            "type": parsed.get("jenis", "pengeluaran"),
            "amount": parsed.get("nominal", 0),
            "category": parsed.get("kategori", "lainnya_biaya"),
            "note": parsed.get("catatan", ""),
            "date": parsed.get("tanggal"),
            "quantity": parsed.get("quantity"),
            "unit": parsed.get("unit"),
        }

        # Skip transactions with 0 amount
        if mapped["amount"] <= 0:
            await send_message(chat_id, "⚠️ Nominal tidak valid. Contoh: 'beli kain 5 meter 250rb' atau 'jual seragam 10 pcs 850rb'.")
            return

        transaction = TransactionService.create_transaction(
            db,
            user_id=user.id,
            parsed=mapped,
            raw_message=text,
            source="telegram",
        )

        # Sync to Google Sheets
        try:
            google_sheets_service.append_transaction(
                tanggal=transaction.date,
                jenis=transaction.type,
                kategori=mapped["category"],
                nominal=transaction.amount,
                catatan=transaction.note,
                sumber="telegram",
                quantity=transaction.quantity,
                unit=transaction.unit,
                price_per_unit=transaction.price_per_unit,
            )
            logger.info("✅ Synced to Google Sheets: %s %s", transaction.type, mapped["category"])
        except Exception as e:
            logger.warning("Failed to sync to Google Sheets: %s", e)

        reply = ResponseFormatter.format_transaction_reply(transaction)
        await send_message(chat_id, reply)

    except Exception as exc:
        logger.exception("Error processing message: %s", exc)
        try:
            await send_message(chat_id, "⚠️ Terjadi kesalahan internal. Silakan coba lagi.")
        except Exception:
            pass


async def handle_callback_query(callback_query: dict, db) -> None:
    """Handle inline keyboard button presses."""
    chat_id = str(callback_query["message"]["chat"]["id"])
    data = callback_query.get("data", "")
    from_user = callback_query.get("from", {})
    telegram_user_id = str(from_user.get("id", ""))
    user_name = from_user.get("first_name", "")

    if not data.startswith("/"):
        return

    try:
        user = TransactionService.get_or_create_user(
            db,
            platform="telegram",
            platform_id=telegram_user_id or chat_id,
            name=user_name,
        )
        await handle_command(data, chat_id, user.id, db)

        # Answer callback query to remove loading state
        url = f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json={"callback_query_id": callback_query["id"]})

    except Exception as exc:
        logger.exception("Error handling callback query: %s", exc)


async def poll_updates():
    """Long-polling loop to receive and process Telegram updates."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    logger.info("🤖 Starting Guzsan Finance AI Bot...")
    logger.info("📡 Polling for updates...")

    # Initialize database
    init_db()
    db = SessionLocal()
    try:
        seed_categories(db)
        # Seed default marketplaces
        from app.services.konveksi_service import KonveksiService
        KonveksiService.seed_default_marketplaces(db)
        # Setup Google Sheets headers
        try:
            google_sheets_service.setup_headers()
            logger.info("✅ Google Sheets headers configured")
        except Exception as e:
            logger.warning("Failed to setup Google Sheets headers: %s", e)

        # Register bot commands in Telegram menu
        await set_bot_commands()

        offset = 0
        while True:
            try:
                url = f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
                params = {"offset": offset, "timeout": 30, "allowed_updates": ["message", "callback_query"]}

                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code != 200:
                        logger.warning("getUpdates failed: %s", resp.text[:200])
                        await asyncio.sleep(5)
                        continue

                    data = resp.json()
                    if not data.get("ok"):
                        logger.warning("getUpdates not ok: %s", data)
                        await asyncio.sleep(5)
                        continue

                    updates = data.get("result", [])
                    for update in updates:
                        offset = update["update_id"] + 1

                        # Handle regular messages
                        message = update.get("message")
                        if message:
                            await process_message(message, db)

                        # Handle inline keyboard button presses
                        callback_query = update.get("callback_query")
                        if callback_query:
                            await handle_callback_query(callback_query, db)

            except httpx.TimeoutException:
                logger.debug("Poll timeout (normal)")
            except Exception as exc:
                logger.error("Poll error: %s", exc)
                await asyncio.sleep(5)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(poll_updates())
