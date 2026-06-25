"""Response formatter for Telegram bot messages."""
from datetime import date


class ResponseFormatter:
    """Format bot responses for Telegram."""

    @staticmethod
    def format_help() -> str:
        """Format help message."""
        return """👋 Selamat Datang di ZYNEFINANCE AI

Asisten keuangan dan bisnis konveksi berbasis AI untuk membantu Anda mencatat transaksi, 
memantau arus kas, menghitung keuntungan, dan mengelola bisnis konveksi.

📊 Semua data akan tersinkron otomatis ke Google Sheets.

📋 Perintah Umum:
/start - Mulai bot
/help atau /bantuan - Lihat bantuan
/ringkasan - Ringkasan bulan ini
/hariini - Pengeluaran hari ini
/mingguini - Laporan mingguan
/bulanini - Rincian bulan ini
/riwayat - 10 transaksi terakhir
/kategori - Breakdown per kategori
/profit - Laporan keuntungan bulanan
/cashflow - Arus kas 30 hari terakhir
/reset - Reset semua data

🏭 Perintah Konveksi:
/stok - Cek stok produk
/bahan - Stok bahan baku
/marketplace - Daftar marketplace
/konveksi - Laporan laba konveksi
/tambah_produk - Tambah produk baru
/tambah_bahan - Tambah bahan baku

💡 Kirim pesan biasa untuk mencatat transaksi:
• "makan siang 25rb"
• "gaji 5 juta"
• "jual kaos L 3pcs di shopee 85rb"
• "produksi kaos L 10pcs"
• "beli kain 10 meter 250rb"
"""

    @staticmethod
    def format_transaction_reply(transaction) -> str:
        """Format a transaction confirmation reply."""
        icon = "✅" if transaction.type == "pemasukan" else "💸"
        type_label = "Pemasukan" if transaction.type == "pemasukan" else "Pengeluaran"

        # Get category info
        category_name = "lainnya"
        if hasattr(transaction, 'category') and transaction.category:
            category_name = transaction.category.name
            if transaction.category.icon:
                icon = transaction.category.icon

        amount_str = f"Rp {transaction.amount:,.0f}".replace(",", ".")

        lines = [
            f"{icon} *{type_label} Tercatat!*",
            f"",
            f"📅 Tanggal: {transaction.date}",
            f"📁 Kategori: {category_name}",
            f"💰 Nominal: {amount_str}",
        ]

        # Show quantity/unit and price per unit if available
        if hasattr(transaction, 'quantity') and transaction.quantity and transaction.unit:
            qty = transaction.quantity
            unit = transaction.unit
            ppu = transaction.price_per_unit or 0
            ppu_str = f"Rp {ppu:,.0f}".replace(",", ".")
            # Format quantity: remove trailing .0 for whole numbers
            qty_str = f"{qty:g}"
            lines.append(f"📦 Jumlah: {qty_str} {unit}")
            lines.append(f"💲 Harga/{unit}: {ppu_str}")

        lines.extend([
            f"📝 Catatan: {transaction.note or '-'}",
            f"🔗 Sumber: {transaction.source}",
            f"",
            f"📊 Data sudah tersimpan dan tersinkron ke Google Sheets.",
        ])

        return "\n".join(lines)

    @staticmethod
    def format_summary(summary: dict) -> str:
        """Format a financial summary."""
        start = summary.get("start_date", "?")
        end = summary.get("end_date", "?")

        pemasukan = summary.get("pemasukan", 0)
        pengeluaran = summary.get("pengeluaran", 0)
        saldo = summary.get("saldo", 0)
        total_transaksi = summary.get("total_transaksi", 0)

        p_str = f"Rp {pemasukan:,.0f}".replace(",", ".")
        e_str = f"Rp {pengeluaran:,.0f}".replace(",", ".")
        s_str = f"Rp {saldo:,.0f}".replace(",", ".")

        saldo_icon = "📈" if saldo >= 0 else "📉"

        return f"""📊 *Ringkasan Keuangan*
📅 Periode: {start} s/d {end}

💰 Pemasukan: {p_str}
💸 Pengeluaran: {e_str}
{saldo_icon} Saldo: {s_str}
📋 Total Transaksi: {total_transaksi}
"""

    @staticmethod
    def format_transaction_list(transactions: list) -> str:
        """Format a list of transactions."""
        if not transactions:
            return "📋 Belum ada transaksi."

        lines = ["📋 *10 Transaksi Terakhir*\n"]

        for i, t in enumerate(transactions, 1):
            icon = "💰" if t.type == "pemasukan" else "💸"
            amount_str = f"Rp {t.amount:,.0f}".replace(",", ".")
            category_name = "lainnya"
            if hasattr(t, 'category') and t.category:
                category_name = t.category.name
                if t.category.icon:
                    icon = t.category.icon

            lines.append(f"{i}. {icon} {t.date} - {category_name}: {amount_str}")
            if t.note:
                lines.append(f"   📝 {t.note}")

        return "\n".join(lines)

    @staticmethod
    def format_category_breakdown(breakdown: list) -> str:
        """Format category breakdown."""
        if not breakdown:
            return "📊 Belum ada data kategori."

        lines = ["📊 *Breakdown per Kategori*\n"]

        pengeluaran = [b for b in breakdown if b["type"] == "pengeluaran"]
        pemasukan = [b for b in breakdown if b["type"] == "pemasukan"]

        if pengeluaran:
            lines.append("💸 *Pengeluaran:*")
            for b in pengeluaran:
                icon = b.get("icon", "📦")
                total_str = f"Rp {b['total']:,.0f}".replace(",", ".")
                lines.append(f"  {icon} {b['category']}: {total_str} ({b['count']}x)")

        if pemasukan:
            lines.append("\n💰 *Pemasukan:*")
            for b in pemasukan:
                icon = b.get("icon", "💵")
                total_str = f"Rp {b['total']:,.0f}".replace(",", ".")
                lines.append(f"  {icon} {b['category']}: {total_str} ({b['count']}x)")

        return "\n".join(lines)

    @staticmethod
    def format_daily_report(daily: list) -> str:
        """Format daily report."""
        if not daily:
            return "📅 Belum ada data hari ini."

        lines = ["📅 *Laporan Harian*\n"]

        for d in daily:
            p_str = f"Rp {d['pemasukan']:,.0f}".replace(",", ".")
            e_str = f"Rp {d['pengeluaran']:,.0f}".replace(",", ".")
            saldo = d['pemasukan'] - d['pengeluaran']
            s_str = f"Rp {saldo:,.0f}".replace(",", ".")
            saldo_icon = "📈" if saldo >= 0 else "📉"

            lines.append(f"📆 {d['date']}")
            lines.append(f"  💰 Masuk: {p_str}")
            lines.append(f"  💸 Keluar: {e_str}")
            lines.append(f"  {saldo_icon} Saldo: {s_str}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_weekly_report(summary: dict, daily: list, breakdown: list) -> str:
        """Format a comprehensive weekly report."""
        start = summary.get("start_date", "?")
        end = summary.get("end_date", "?")
        pemasukan = summary.get("pemasukan", 0)
        pengeluaran = summary.get("pengeluaran", 0)
        saldo = summary.get("saldo", 0)
        total_transaksi = summary.get("total_transaksi", 0)

        p_str = f"Rp {pemasukan:,.0f}".replace(",", ".")
        e_str = f"Rp {pengeluaran:,.0f}".replace(",", ".")
        s_str = f"Rp {saldo:,.0f}".replace(",", ".")
        saldo_icon = "📈" if saldo >= 0 else "📉"

        # Day names in Indonesian
        day_names = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]

        lines = [
            f"📆 *Laporan Mingguan*",
            f"📅 {start} s/d {end}\n",
            f"💰 Pemasukan: {p_str}",
            f"💸 Pengeluaran: {e_str}",
            f"{saldo_icon} Saldo: {s_str}",
            f"📋 Total Transaksi: {total_transaksi}\n",
        ]

        # Daily breakdown
        if daily:
            lines.append("📊 *Harian:*")
            for d in daily:
                from datetime import date as dt
                try:
                    dt_obj = dt.fromisoformat(d['date'])
                    day_name = day_names[dt_obj.weekday()]
                    date_label = f"{day_name} {dt_obj.day}/{dt_obj.month}"
                except:
                    date_label = d['date']

                e_daily = f"Rp {d['pengeluaran']:,.0f}".replace(",", ".")
                p_daily = f"Rp {d['pemasukan']:,.0f}".replace(",", ".")
                lines.append(f"  📆 {date_label}: Kel {e_daily}" + (f", Masuk {p_daily}" if d['pemasukan'] > 0 else ""))
            lines.append("")

        # Category breakdown
        if breakdown:
            pengeluaran_cats = [b for b in breakdown if b["type"] == "pengeluaran"]
            pemasukan_cats = [b for b in breakdown if b["type"] == "pemasukan"]

            if pengeluaran_cats:
                lines.append("💸 *Kategori Pengeluaran:*")
                for b in pengeluaran_cats[:5]:  # Top 5
                    icon = b.get("icon", "📦")
                    total_str = f"Rp {b['total']:,.0f}".replace(",", ".")
                    lines.append(f"  {icon} {b['category']}: {total_str} ({b['count']}x)")

            if pemasukan_cats:
                lines.append("\n💰 *Kategori Pemasukan:*")
                for b in pemasukan_cats:
                    icon = b.get("icon", "💵")
                    total_str = f"Rp {b['total']:,.0f}".replace(",", ".")
                    lines.append(f"  {icon} {b['category']}: {total_str} ({b['count']}x)")

        return "\n".join(lines)

    @staticmethod
    def format_monthly_report(monthly: list, year: int) -> str:
        """Format monthly report."""
        if not monthly:
            return f"📅 Belum ada data untuk tahun {year}."

        lines = [f"📅 *Laporan Bulanan {year}*\n"]

        for m in monthly:
            p_str = f"Rp {m['pemasukan']:,.0f}".replace(",", ".")
            e_str = f"Rp {m['pengeluaran']:,.0f}".replace(",", ".")
            saldo = m['pemasukan'] - m['pengeluaran']
            s_str = f"Rp {saldo:,.0f}".replace(",", ".")
            saldo_icon = "📈" if saldo >= 0 else "📉"

            lines.append(f"📆 {m['month']}")
            lines.append(f"  💰 Masuk: {p_str}")
            lines.append(f"  💸 Keluar: {e_str}")
            lines.append(f"  {saldo_icon} Saldo: {s_str}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_today_report(summary: dict, transactions: list) -> str:
        """Format today's report with summary and transaction list."""
        pemasukan = summary.get("pemasukan", 0)
        pengeluaran = summary.get("pengeluaran", 0)
        saldo = summary.get("saldo", 0)
        total = summary.get("total_transaksi", 0)

        p_str = f"Rp {pemasukan:,.0f}".replace(",", ".")
        e_str = f"Rp {pengeluaran:,.0f}".replace(",", ".")
        s_str = f"Rp {saldo:,.0f}".replace(",", ".")
        saldo_icon = "📈" if saldo >= 0 else "📉"

        lines = [
            f"📅 *Hari Ini*",
            f"💰 Pemasukan: {p_str}",
            f"💸 Pengeluaran: {e_str}",
            f"{saldo_icon} Saldo: {s_str}",
            f"📋 Total Transaksi: {total}\n",
        ]

        if transactions:
            lines.append("📝 *Transaksi Hari Ini:*")
            for i, t in enumerate(transactions, 1):
                icon = "💰" if t.type == "pemasukan" else "💸"
                amount_str = f"Rp {t.amount:,.0f}".replace(",", ".")
                category_name = "lainnya"
                if hasattr(t, 'category') and t.category:
                    category_name = t.category.name
                    if t.category.icon:
                        icon = t.category.icon
                lines.append(f"  {i}. {icon} {category_name}: {amount_str}")
                if t.note:
                    lines.append(f"     📝 {t.note}")
        else:
            lines.append("Belum ada transaksi hari ini.")

        return "\n".join(lines)

    @staticmethod
    def format_cashflow_report(daily: list) -> str:
        """Format cashflow report (30 days) — synced with dashboard logic.

        Dashboard returns: {day, income, expense}
        Bot returns: {date, pemasukan, pengeluaran}
        Format output matches dashboard structure.
        """
        if not daily:
            return "📅 Belum ada data arus kas."

        # Day names in Indonesian
        day_names = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]

        lines = ["📊 *Arus Kas 30 Hari Terakhir*\n"]

        total_income = 0
        total_expense = 0

        for d in daily:
            from datetime import date as dt
            try:
                dt_obj = dt.fromisoformat(d['date'])
                day_name = day_names[dt_obj.weekday()]
                date_label = f"{day_name} {dt_obj.day}/{dt_obj.month}"
            except:
                date_label = d['date']

            income = d.get('pemasukan', 0)
            expense = d.get('pengeluaran', 0)
            total_income += income
            total_expense += expense

            i_str = f"Rp {income:,.0f}".replace(",", ".")
            e_str = f"Rp {expense:,.0f}".replace(",", ".")
            net = income - expense
            net_str = f"Rp {net:,.0f}".replace(",", ".")
            net_icon = "📈" if net >= 0 else "📉"

            lines.append(f"📆 {date_label}")
            lines.append(f"  💰 Masuk: {i_str}")
            lines.append(f"  💸 Keluar: {e_str}")
            lines.append(f"  {net_icon} Net: {net_str}")
            lines.append("")

        # Summary
        total_net = total_income - total_expense
        net_icon = "📈" if total_net >= 0 else "📉"
        lines.append("📊 *Total 30 Hari:*")
        lines.append(f"  💰 Total Masuk: Rp {total_income:,.0f}".replace(",", "."))
        lines.append(f"  💸 Total Keluar: Rp {total_expense:,.0f}".replace(",", "."))
        lines.append(f"  {net_icon} Net: Rp {total_net:,.0f}".replace(",", "."))

        return "\n".join(lines)
