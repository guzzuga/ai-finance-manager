"""Konveksi response formatter for Telegram bot messages."""
from datetime import date


class KonveksiFormatter:
    """Format konveksi-related bot responses."""

    @staticmethod
    def format_sale_reply(sale) -> str:
        """Format a sale confirmation reply."""
        product_name = sale.product.name if hasattr(sale, 'product') and sale.product else "Produk"
        mp_name = sale.marketplace.name if hasattr(sale, 'marketplace') and sale.marketplace else "Marketplace"
        mp_icon = sale.marketplace.icon if hasattr(sale, 'marketplace') and sale.marketplace else "🛒"

        revenue_str = f"Rp {sale.total_revenue:,.0f}".replace(",", ".")
        hpp_str = f"Rp {sale.total_hpp:,.0f}".replace(",", ".")
        fee_str = f"Rp {sale.marketplace_fee:,.0f}".replace(",", ".")
        profit_str = f"Rp {sale.profit:,.0f}".replace(",", ".")
        net_str = f"Rp {sale.net_revenue:,.0f}".replace(",", ".")
        ppu_str = f"Rp {sale.price_per_unit:,.0f}".replace(",", ".")

        lines = [
            f"✅ *Penjualan Tercatat!*",
            f"",
            f"📦 Produk: {product_name}",
            f"{mp_icon} Marketplace: {mp_name}",
            f"📅 Tanggal: {sale.date}",
            f"📊 Qty: {sale.quantity} pcs × {ppu_str}",
            f"",
            f"💰 Revenue: {revenue_str}",
            f"📉 HPP: {hpp_str}",
            f"🏪 Fee {mp_name}: {fee_str}",
            f"📈 Laba Bersih: {profit_str}",
            f"",
            f"💵 Net Revenue: {net_str}",
            f"📆 Est. Cair: {sale.settlement_date or '-'}",
        ]

        if sale.order_id:
            lines.insert(4, f"🔖 Order: {sale.order_id}")

        return "\n".join(lines)

    @staticmethod
    def format_production_reply(production) -> str:
        """Format a production confirmation reply."""
        product_name = production.product.name if hasattr(production, 'product') and production.product else "Produk"

        cost_str = f"Rp {production.total_cost:,.0f}".replace(",", ".")
        cpu_str = f"Rp {production.cost_per_unit:,.0f}".replace(",", ".")

        lines = [
            f"✅ *Produksi Tercatat!*",
            f"",
            f"📦 Produk: {product_name}",
            f"📅 Tanggal: {production.date}",
            f"📊 Qty: {production.quantity} pcs",
            f"💰 Biaya/pcs: {cpu_str}",
            f"💸 Total Biaya: {cost_str}",
            f"📈 Stok bertambah: +{production.quantity} pcs",
        ]

        if production.notes:
            lines.append(f"📝 Catatan: {production.notes}")

        return "\n".join(lines)

    @staticmethod
    def format_stock_report(products: list) -> str:
        """Format stock report."""
        if not products:
            return "📦 Belum ada produk. Tambah produk dengan /tambah_produk"

        lines = ["📦 *Stok Produk Konveksi*\n"]

        for p in products:
            stock_icon = "🟢" if p.stock > (p.min_stock or 0) else "🔴"
            hpp_str = f"Rp {p.hpp:,.0f}".replace(",", ".")
            price_str = f"Rp {p.price:,.0f}".replace(",", ".")
            margin = p.price - p.hpp if p.price > 0 and p.hpp > 0 else 0
            margin_str = f"Rp {margin:,.0f}".replace(",", ".")

            lines.append(f"{stock_icon} *{p.name}*")
            lines.append(f"  Stok: {p.stock} {p.unit}")
            lines.append(f"  HPP: {hpp_str} | Jual: {price_str}")
            lines.append(f"  Margin: {margin_str}/pcs")
            if p.min_stock and p.stock <= p.min_stock:
                lines.append(f"  ⚠️ *STOK RENDAH!* (min: {p.min_stock})")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_laporan_konveksi(report: dict, start_date: str, end_date: str) -> str:
        """Format konveksi profit/loss report."""
        def fmt(val):
            return f"Rp {val:,.0f}".replace(",", ".")

        profit_icon = "📈" if report["total_profit"] >= 0 else "📉"
        margin = (report["total_profit"] / report["total_revenue"] * 100) if report["total_revenue"] > 0 else 0

        lines = [
            f"📊 *Laporan Konveksi*",
            f"📅 {start_date} s/d {end_date}",
            f"",
            f"💰 Total Revenue: {fmt(report['total_revenue'])}",
            f"📉 Total HPP: {fmt(report['total_hpp'])}",
            f"🏪 Total Fee Marketplace: {fmt(report['total_fee'])}",
            f"🚚 Total Ongkir: {fmt(report['total_shipping'])}",
            f"💸 Total Biaya Produksi: {fmt(report['total_production_cost'])}",
            f"",
            f"{profit_icon} LABA BERSIH: {fmt(report['total_profit'])}",
            f"📊 Margin: {margin:.1f}%",
            f"",
            f"📦 Terjual: {report['total_qty_sold']} pcs ({report['total_orders']} order)",
            f"🏭 Diproduksi: {report['total_produced']} pcs",
        ]

        # Marketplace breakdown
        if report["marketplace_breakdown"]:
            lines.append("")
            lines.append("🛒 *Per Marketplace:*")
            for mp in report["marketplace_breakdown"]:
                icon = mp.get("icon", "🛒")
                profit_mp = f"Rp {mp['profit']:,.0f}".replace(",", ".")
                lines.append(f"  {icon} {mp['name']}: {mp['qty']} pcs, laba {profit_mp}")

        # Product breakdown
        if report["product_breakdown"]:
            lines.append("")
            lines.append("📦 *Per Produk:*")
            for p in report["product_breakdown"]:
                profit_p = f"Rp {p['profit']:,.0f}".replace(",", ".")
                lines.append(f"  • {p['name']}: {p['qty']} pcs, laba {profit_p}")

        return "\n".join(lines)

    @staticmethod
    def format_marketplace_list(marketplaces: list) -> str:
        """Format marketplace list."""
        if not marketplaces:
            return "🛒 Belum ada marketplace."

        lines = ["🛒 *Daftar Marketplace*\n"]
        for mp in marketplaces:
            icon = mp.icon or "🛒"
            lines.append(f"{icon} *{mp.name}*")
            lines.append(f"  Fee: {mp.fee_percent}% + Rp {mp.fee_fixed:,}")
            lines.append(f"  Cair: {mp.settlement_days} hari")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_material_list(materials: list) -> str:
        """Format material stock list."""
        if not materials:
            return "🧵 Belum ada bahan baku."

        lines = ["🧵 *Stok Bahan Baku*\n"]
        for m in materials:
            stock_icon = "🟢" if m.stock > (m.min_stock or 0) else "🔴"
            price_str = f"Rp {m.price_per_unit:,.0f}".replace(",", ".")
            lines.append(f"{stock_icon} *{m.name}*")
            lines.append(f"  Stok: {m.stock} {m.unit}")
            lines.append(f"  Harga: {price_str}/{m.unit}")
            if m.supplier:
                lines.append(f"  Supplier: {m.supplier}")
            if m.min_stock and m.stock <= m.min_stock:
                lines.append(f"  ⚠️ *STOK RENDAH!*")
            lines.append("")

        return "\n".join(lines)
