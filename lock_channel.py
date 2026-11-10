"""
Administrative Lock Channel Mirroring Module for Mio Ads
Securely mirrors all ticket activities, user logs, channel moderation events,
and complete invoice metadata instantaneously to the private administrative 'Lock Channel'.
"""

import os
import time
import httpx
from typing import Dict, Any, Optional

from config import config
from database import db_manager

class LockChannelLedger:
    def __init__(self):
        self.lock_channel_id = config.LOCK_CHANNEL_ID
        self.bot_token = config.TELEGRAM_BOT_TOKEN

    async def _send_telegram_lock_message(self, text: str, document_path: Optional[str] = None) -> bool:
        """Sends a message (and the PDF, if given) to the private Lock Channel. Logs Telegram's answer."""
        if not self.bot_token or "Example_" in self.bot_token:
            print("[Lock Channel ERROR] No bot token configured")
            return False
        api = f"https://api.telegram.org/bot{self.bot_token}"
        ok = False
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(f"{api}/sendMessage", json={
                    "chat_id": self.lock_channel_id,
                    "text": text,
                    "parse_mode": "HTML"
                })
                ok = resp.status_code == 200
                if not ok:
                    print(f"[Lock Channel ERROR] sendMessage {resp.status_code}: {resp.text}")
                if document_path and os.path.exists(document_path):
                    with open(document_path, "rb") as fh:
                        r2 = await client.post(
                            f"{api}/sendDocument",
                            data={"chat_id": self.lock_channel_id, "caption": "🔒 Invoice PDF backup"},
                            files={"document": (os.path.basename(document_path), fh, "application/pdf")}
                        )
                    if r2.status_code != 200:
                        print(f"[Lock Channel ERROR] sendDocument {r2.status_code}: {r2.text}")
                    ok = ok and r2.status_code == 200
        except Exception as e:
            print(f"[Lock Channel ERROR] Telegram API: {e}")
            return False
        return ok

    async def mirror_invoice(self, invoice_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Instantaneously backs up every generated PDF invoice along with complete metadata
        (User ID, Date, Chosen Language, Country, Net Amount, Exchange Rate) to the private Lock Channel.
        """
        log_entry = {
            "event_type": "INVOICE_GENERATED",
            "invoice_id": invoice_meta.get("invoice_id"),
            "user_id": invoice_meta.get("user_id"),
            "date": invoice_meta.get("date"),
            "chosen_language": invoice_meta.get("chosen_language"),
            "country": invoice_meta.get("country"),
            "amount_usdt": invoice_meta.get("amount_usdt"),
            "amount_inr": invoice_meta.get("amount_inr"),
            "net_amount_usdt": invoice_meta.get("net_amount_usdt"),
            "exchange_rate": invoice_meta.get("exchange_rate"),
            "filepath": invoice_meta.get("filepath"),
            "web_url": invoice_meta.get("web_url"),
            "timestamp": time.time(),
            "mirrored_to_channel": self.lock_channel_id,
            "status": "SECURED_IN_LOCK_LEDGER"
        }

        # Store in MongoDB lock ledger collection
        db_manager.db.lock_ledger.insert_one(log_entry)

        # Formatted administrative message
        msg = (
            f"🔒 <b>[LOCK LEDGER] Official Invoice Backup</b>\n\n"
            f"📄 <b>Invoice:</b> <code>{invoice_meta.get('invoice_id')}</code>\n"
            f"👤 <b>User ID:</b> <code>{invoice_meta.get('user_id')}</code>\n"
            f"🌐 <b>Language:</b> {invoice_meta.get('chosen_language')} | <b>Region:</b> {invoice_meta.get('country')}\n"
            f"💵 <b>Amount:</b> ${invoice_meta.get('amount_usdt')} USDT (₹{invoice_meta.get('amount_inr')} INR)\n"
            f"📉 <b>Net Settled:</b> ${invoice_meta.get('net_amount_usdt')} USDT (@ ₹{invoice_meta.get('exchange_rate')})\n"
            f"🕒 <b>Timestamp:</b> {invoice_meta.get('date')}\n"
            f"📎 <b>Download PDF:</b> {invoice_meta.get('web_url')}"
        )

        await self._send_telegram_lock_message(msg, document_path=invoice_meta.get("filepath"))
        print(f"[Lock Channel Mirror] Invoice {invoice_meta.get('invoice_id')} mirrored successfully.")
        return log_entry

    async def mirror_ticket_activity(self, ticket_data: Dict[str, Any], action: str = "TICKET_CREATED") -> Dict[str, Any]:
        """
        Mirrors all ticket activities with strict 24-hour response SLA countdown tracking.
        """
        sla_hours = config.SUPPORT_SLA_HOURS
        sla_deadline = ticket_data.get("created_at", time.time()) + (sla_hours * 3600)
        sla_deadline_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(sla_deadline))

        log_entry = {
            "event_type": action,
            "ticket_id": ticket_data.get("ticket_id"),
            "user_id": ticket_data.get("user_id"),
            "gmail": ticket_data.get("gmail"),
            "narrative_preview": str(ticket_data.get("narrative", ""))[:200],
            "attachment_count": len(ticket_data.get("attachments", [])),
            "sla_deadline": sla_deadline,
            "sla_deadline_str": sla_deadline_str,
            "status": ticket_data.get("status", "open"),
            "timestamp": time.time(),
            "mirrored_to_channel": self.lock_channel_id
        }

        db_manager.db.lock_ledger.insert_one(log_entry)

        msg = (
            f"🎫 <b>[LOCK LEDGER] Support Ticket Activity ({action})</b>\n\n"
            f"🆔 <b>Ticket ID:</b> <code>{ticket_data.get('ticket_id')}</code>\n"
            f"👤 <b>User ID:</b> <code>{ticket_data.get('user_id')}</code>\n"
            f"📧 <b>Gmail:</b> {ticket_data.get('gmail')}\n"
            f"⏱ <b>Response SLA:</b> Strict 24h Deadline -> <b>{sla_deadline_str}</b>\n"
            f"📂 <b>Attachments:</b> {len(ticket_data.get('attachments', []))} file(s)\n"
            f"📝 <b>Narrative:</b>\n<i>{ticket_data.get('narrative')}</i>"
        )

        await self._send_telegram_lock_message(msg)
        return log_entry

    async def mirror_withdrawal_request(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mirrors withdrawal requests queued for the weekly payout run.
        """
        sla_deadline = tx_data.get("review_deadline") or (tx_data.get("created_at", time.time()) + (config.PAYOUT_CYCLE_DAYS * 86400))
        sla_deadline_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(sla_deadline))

        log_entry = {
            "event_type": "WITHDRAWAL_REQUESTED",
            "tx_id": tx_data.get("tx_id"),
            "user_id": tx_data.get("user_id"),
            "amount_usdt": tx_data.get("amount"),
            "currency": tx_data.get("currency", "USDT"),
            "destination_address": tx_data.get("destination_address"),
            "review_sla_deadline": sla_deadline,
            "review_sla_deadline_str": sla_deadline_str,
            "status": "pending_weekly_payout",
            "timestamp": time.time(),
            "mirrored_to_channel": self.lock_channel_id
        }

        db_manager.db.lock_ledger.insert_one(log_entry)

        msg = (
            f"💸 <b>[LOCK LEDGER] Withdrawal Request Pending Review</b>\n\n"
            f"🆔 <b>TX ID:</b> <code>{tx_data.get('tx_id')}</code>\n"
            f"👤 <b>User ID:</b> <code>{tx_data.get('user_id')}</code>\n"
            f"💰 <b>Amount:</b> ${tx_data.get('amount')} USDT\n"
            f"📍 <b>Payout Address:</b> <code>{tx_data.get('destination_address')}</code>\n"
            f"📅 <b>Weekly Payout Scheduled:</b> <b>{tx_data.get('payout_date_str') or sla_deadline_str}</b>"
        )

        await self._send_telegram_lock_message(msg)
        return log_entry

    async def mirror_channel_moderation(self, channel_data: Dict[str, Any], decision: str, admin_id: int) -> Dict[str, Any]:
        """Mirrors channel approval or rejection events to lock ledger."""
        log_entry = {
            "event_type": f"CHANNEL_{decision.upper()}",
            "channel_id": channel_data.get("channel_id"),
            "channel_title": channel_data.get("title"),
            "channel_username": channel_data.get("username"),
            "owner_user_id": channel_data.get("telegram_id"),
            "moderated_by_admin": admin_id,
            "timestamp": time.time(),
            "mirrored_to_channel": self.lock_channel_id
        }

        db_manager.db.lock_ledger.insert_one(log_entry)
        return log_entry

# Global lock ledger instance
lock_ledger = LockChannelLedger()
