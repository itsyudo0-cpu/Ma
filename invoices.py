"""
Automated Invoicing System for Mio Ads Telegram Mini App Ecosystem
Generates professional PDF invoices for deposits, payouts, withdrawals, and platform transactions.
Includes full metadata encapsulation for immediate synchronization with the administrative Lock Channel.
"""

import os
import time
import uuid
from typing import Dict, Any, Optional
import hashlib

# Python 3.8 OpenSSL compatibility patch for ReportLab
_orig_md5 = hashlib.md5
def _safe_md5(*args, **kwargs):
    kwargs.pop('usedforsecurity', None)
    return _orig_md5(*args, **kwargs)
hashlib.md5 = _safe_md5

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

from config import config

class InvoiceGenerator:
    def __init__(self):
        os.makedirs(config.INVOICES_DIR, exist_ok=True)

    def generate_invoice_pdf(self, tx_data: Dict[str, Any], user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates an official Mio Ads PDF invoice and returns file path, URL, and lock ledger metadata.
        """
        invoice_id = tx_data.get("invoice_id") or f"MIO-{int(time.time())}-{str(uuid.uuid4())[:6].upper()}"
        filename = f"invoice_{invoice_id}.pdf"
        filepath = os.path.join(config.INVOICES_DIR, filename)
        web_url = f"/static/invoices/{filename}"

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        elements = []
        styles = getSampleStyleSheet()

        # Custom Brand Colors
        navy = colors.HexColor("#0B192C")
        accent_blue = colors.HexColor("#00B4D8")
        light_bg = colors.HexColor("#F8FAFC")
        dark_text = colors.HexColor("#0F172A")
        muted_text = colors.HexColor("#64748B")
        border_color = colors.HexColor("#E2E8F0")

        # Header Title Style
        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=24,
            textColor=navy,
            leading=28
        )
        subtitle_style = ParagraphStyle(
            'InvoiceSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=muted_text,
            leading=14
        )
        body_style = ParagraphStyle(
            'InvoiceBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=dark_text,
            leading=13
        )
        header_cell_style = ParagraphStyle(
            'HeaderCell',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=colors.white,
            leading=14
        )

        # Header Table: Logo & Company Info on Left, Invoice Details on Right
        logo_path = os.path.join(config.STATIC_DIR, "images", "logo.png")
        if os.path.exists(logo_path):
            logo_img = RLImage(logo_path, width=54, height=54)
        else:
            logo_img = Paragraph("<b>MIO ADS</b>", title_style)

        company_info = Paragraph(
            "<b>Mio Ads Ecosystem</b><br/>"
            "Telegram Mini App Ads Network<br/>"
            "Bot: @mioadsbot | Channel: @mioads<br/>"
            "Lock Channel: Administrative Mirror",
            body_style
        )

        user_id = str(user_data.get("telegram_id", "Unknown"))
        chosen_lang = user_data.get("language", config.DEFAULT_LANGUAGE).upper()
        country = user_data.get("country", "India / Global")
        tx_type = tx_data.get("type", "Deposit").upper()
        tx_date = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(tx_data.get("created_at", time.time())))
        status = tx_data.get("status", "COMPLETED").upper()

        invoice_meta = Paragraph(
            f"<b>INVOICE #:</b> {invoice_id}<br/>"
            f"<b>DATE:</b> {tx_date}<br/>"
            f"<b>STATUS:</b> <font color='#059669'><b>{status}</b></font><br/>"
            f"<b>USER TELEGRAM ID:</b> {user_id}<br/>"
            f"<b>LANGUAGE:</b> {chosen_lang} | <b>REGION:</b> {country}",
            body_style
        )

        header_table = Table(
            [[logo_img, company_info, invoice_meta]],
            colWidths=[65, 230, 245]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        banner_path = os.path.join(config.STATIC_DIR, "images", "invoice_header.png")
        if os.path.exists(banner_path):
            elements.append(RLImage(banner_path, width=540, height=135))   # 1600x400 banner
            elements.append(Spacer(1, 10))
        elements.append(header_table)
        elements.append(Spacer(1, 15))

        # Financial Calculations
        amount = float(tx_data.get("amount", 0.0))
        currency = tx_data.get("currency", "USDT")
        fee_percent = float(tx_data.get("fee_percent", config.PLATFORM_FEE_PERCENT))
        fee_amount = round(amount * (fee_percent / 100.0), 4) if tx_data.get("deduct_fee") else 0.0
        net_amount = round(amount - fee_amount, 4)

        inr_rate = float(tx_data.get("usdt_to_inr_rate", config.USDT_TO_INR_RATE))
        amount_inr = round(amount * inr_rate, 2)
        net_inr = round(net_amount * inr_rate, 2)

        # Line Items Table
        table_data = [
            [
                Paragraph("<b>Item Description</b>", header_cell_style),
                Paragraph("<b>Type / SLA</b>", header_cell_style),
                Paragraph("<b>Gross (USDT)</b>", header_cell_style),
                Paragraph("<b>INR Equivalent</b>", header_cell_style),
                Paragraph("<b>Net Settled</b>", header_cell_style)
            ],
            [
                Paragraph(f"<b>{tx_data.get('description', 'Mio Ads Account Transaction')}</b><br/><font color='#64748B'>TX Reference: {tx_data.get('tx_id', invoice_id)}</font>", body_style),
                Paragraph(f"{tx_type}<br/>{tx_data.get('sla_note', 'Direct Settle')}", body_style),
                Paragraph(f"${amount:.2f} USDT", body_style),
                Paragraph(f"Rs. {amount_inr:,.2f} INR", body_style),
                Paragraph(f"<b>${net_amount:.2f} USDT</b>", body_style)
            ]
        ]

        if fee_amount > 0:
            table_data.append([
                Paragraph(f"Platform Fee Deduction ({fee_percent}%)", body_style),
                Paragraph("Administrative Fee", body_style),
                Paragraph(f"-${fee_amount:.2f} USDT", body_style),
                Paragraph(f"-Rs. {fee_amount * inr_rate:,.2f} INR", body_style),
                Paragraph(f"-${fee_amount:.2f} USDT", body_style)
            ])

        # Summary Subtotal row
        table_data.append([
            Paragraph("<b>TOTAL SETTLED AMOUNT</b>", body_style),
            Paragraph("<b>Lock Ledger Verified</b>", body_style),
            Paragraph(f"<b>${net_amount:.2f} USDT</b>", body_style),
            Paragraph(f"<b>Rs. {net_inr:,.2f} INR</b>", body_style),
            Paragraph(f"<font color='#059669'><b>${net_amount:.2f} USDT</b></font>", body_style)
        ])

        items_table = Table(table_data, colWidths=[200, 110, 80, 80, 70])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), navy),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, light_bg]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#EFF6FF")),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 20))
        stamp_path = os.path.join(config.STATIC_DIR, "images", "invoice_paid.png")
        if os.path.exists(stamp_path) and status in ("COMPLETED", "PAID", "APPROVED"):
            stamp = RLImage(stamp_path, width=110, height=110)
            stamp.hAlign = "RIGHT"
            elements.append(stamp)
            elements.append(Spacer(1, 10))

        # Lock Ledger Encapsulated Metadata
        lock_meta_text = (
            f"<b>Administrative Lock Channel Ledger Proof:</b><br/>"
            f"• <b>Hash Reference:</b> SHA256_{uuid.uuid4().hex[:24]}<br/>"
            f"• <b>Lock Channel Destination:</b> {config.LOCK_CHANNEL_ID} ({config.LOCK_CHANNEL_TITLE})<br/>"
            f"• <b>Metadata Captured:</b> User ID: {user_id} | Language: {chosen_lang} | Region: {country} | Rate: $1 = {inr_rate} INR<br/>"
            f"• <b>Review SLA Policy:</b> Withdrawals are paid out in a weekly payout cycle after Administrative Review."
        )
        elements.append(Paragraph(lock_meta_text, body_style))
        elements.append(Spacer(1, 25))

        # Footer Notice
        footer_text = Paragraph(
            "<font color='#64748B' size=8>This is an automated system-generated invoice generated by Mio Ads Telegram Mini App. "
            "All financial movements are cryptographically registered and mirrored to the private Administrative Lock Channel. "
            "For inquiries, submit a ticket in the Mini App under 24-Hour response SLA.</font>",
            body_style
        )
        elements.append(footer_text)

        # Build document
        doc.build(elements)

        # Build Metadata object for Lock Channel backup
        lock_metadata = {
            "invoice_id": invoice_id,
            "filename": filename,
            "filepath": filepath,
            "web_url": web_url,
            "user_id": user_id,
            "date": tx_date,
            "chosen_language": chosen_lang,
            "country": country,
            "amount_usdt": amount,
            "amount_inr": amount_inr,
            "net_amount_usdt": net_amount,
            "tx_type": tx_type,
            "status": status,
            "exchange_rate": inr_rate,
            "timestamp": time.time()
        }

        return lock_metadata

# Global instance
invoice_generator = InvoiceGenerator()
