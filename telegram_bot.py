"""
Telegram Bot Integration & Command Parser for Mio Ads Ecosystem
Enables direct launching of Telegram Mini App via inline buttons, deep linking for referrals,
and command processing mirrored inside the Mini App interface.
"""

import time
import httpx
from typing import Dict, Any, Optional

from config import config
from database import db_manager

class TelegramBotManager:
    def __init__(self):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.username = config.TELEGRAM_BOT_USERNAME
        self.base_url = config.BASE_URL

    def build_webapp_inline_keyboard(self, text: str = "🚀 Open Mio Ads Mini App") -> Dict[str, Any]:
        """Creates Telegram WebApp inline keyboard markup."""
        return {
            "inline_keyboard": [
                [
                    {
                        "text": text,
                        "web_app": {"url": self.base_url}
                    }
                ],
                [
                    {
                        "text": "📊 Publisher Analytics",
                        "web_app": {"url": f"{self.base_url}?view=stats"}
                    },
                    {
                        "text": "💼 Ads & Campaigns",
                        "web_app": {"url": f"{self.base_url}?view=channels"}
                    }
                ],
                [
                    {
                        "text": "🔒 Lock Ledger Mirror",
                        "url": f"https://t.me/MioAdsLockLedger"
                    },
                    {
                        "text": "💬 24h SLA Support",
                        "web_app": {"url": f"{self.base_url}?view=support"}
                    }
                ]
            ]
        }

    async def handle_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """Parses incoming Telegram webhook updates."""
        if "message" not in update:
            return {"status": "ignored"}

        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        user = msg.get("from", {})
        telegram_id = user.get("id")
        first_name = user.get("first_name", "Telegram User")
        username = user.get("username", "")
        text = msg.get("text", "").strip()
        print(f"[Telegram Webhook] message from {telegram_id}: {text[:60]!r}")

        # Handle Commands
        response_text = ""
        reply_markup = None

        if text.startswith("/start"):
            # Check referral argument: /start ref_ARJUN77
            parts = text.split()
            referred_by = None
            if len(parts) > 1 and parts[1].startswith("ref_"):
                referred_by = parts[1].replace("ref_", "")

            # Ensure user registered in DB
            existing_user = db_manager.db.users.find_one({"telegram_id": telegram_id})
            if not existing_user:
                db_manager.db.users.insert_one({
                    "telegram_id": telegram_id,
                    "username": username,
                    "first_name": first_name,
                    "role": "admin" if telegram_id in config.ADMIN_TELEGRAM_IDS else "user",
                    "preferred_currency": "USDT",
                    "language": "en",
                    "wallet_balance_usdt": 10.00,  # Welcome bonus
                    "wallet_balance_inr": 800.00,
                    "api_key": f"mio_usr_key_{telegram_id}",
                    "referral_code": f"REF{telegram_id}",
                    "referred_by": referred_by,
                    "created_at": time.time()
                })

            response_text = (
                f"👋 <b>Welcome to Mio Ads, {first_name}!</b>\n\n"
                f"The premier decentralized Telegram Ads Network connecting high-growth channels, "
                f"verified publishers, and direct advertisers.\n\n"
                f"✨ <b>Key Ecosystem Highlights:</b>\n"
                f"• 💰 <b>Publishers:</b> Monetize your Telegram channel with verified CPC/CPM campaigns\n"
                f"• 🎯 <b>Advertisers:</b> Launch targeted Telegram ads with strict dwell-time protection\n"
                f"• 🔒 <b>Administrative Lock Ledger:</b> Instant audit trail for all invoices & ticket SLAs\n"
                f"• 🇮🇳 <b>Multi-Currency:</b> Instant UPI (₹500 min) & USDT ($10 min) settlement\n\n"
                f"<i>Tap the button below to launch the Mini App directly!</i>"
            )
            reply_markup = self.build_webapp_inline_keyboard()

        elif text.startswith("/wallet"):
            user_doc = db_manager.db.users.find_one({"telegram_id": telegram_id})
            usdt = user_doc.get("wallet_balance_usdt", 0.0) if user_doc else 0.0
            inr = user_doc.get("wallet_balance_inr", 0.0) if user_doc else 0.0
            response_text = (
                f"💼 <b>Mio Ads Multi-Currency Wallet</b>\n\n"
                f"👤 <b>Telegram ID:</b> <code>{telegram_id}</code>\n"
                f"💵 <b>USDT Balance:</b> ${usdt:.2f} USDT\n"
                f"🇮🇳 <b>INR Balance:</b> ₹{inr:,.2f} INR (@ ₹{config.USDT_TO_INR_RATE})\n\n"
                f"• Minimum Deposit: ₹500 (UPI) / $10 USDT\n"
                f"• Minimum Withdrawal: $5 USDT (Weekly Payout)"
            )
            reply_markup = self.build_webapp_inline_keyboard("💳 Open Wallet in Mini App")

        elif text.startswith("/admin"):
            _u = db_manager.db.users.find_one({"telegram_id": telegram_id})
            if not _u or _u.get("role") != "admin":
                response_text = "⛔ <i>Access Denied: Administrative privileges required.</i>"
            else:
                response_text = (
                    f"🛡 <b>Mio Ads Master Administration Control</b>\n\n"
                    f"• Platform Fee Deduction: <b>{config.PLATFORM_FEE_PERCENT}%</b>\n"
                    f"• Dynamic Exchange Rate: <b>$1 = ₹{config.USDT_TO_INR_RATE} INR</b>\n"
                    f"• Lock Channel ID: <code>{config.LOCK_CHANNEL_ID}</code>\n"
                    f"• MongoDB: <b>{'TEMP MEMORY DB' if db_manager.is_mock else 'Live'}</b> ({len(db_manager.urls)} URL)\n\n"
                    f"Use the Mini App Admin Panel to approve channels, trigger global broadcasts, and switch database URIs."
                )
                reply_markup = {
                    "inline_keyboard": [
                        [{"text": "🛡 Open Admin Panel", "web_app": {"url": f"{self.base_url}?view=admin"}}]
                    ]
                }
        else:
            response_text = (
                f"🤖 <b>Mio Ads Unified Command Interface</b>\n\n"
                f"All operations are parsed directly inside the Telegram Mini App.\n"
                f"Commands: /start, /wallet, /channels, /stats, /help, /admin"
            )
            reply_markup = self.build_webapp_inline_keyboard()

        # Send response via Telegram Bot API if configured
        await self._send_reply(chat_id, response_text, reply_markup)

        return {
            "status": "processed",
            "chat_id": chat_id,
            "response_text": response_text
        }

    async def _send_reply(self, chat_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None):
        """Sends reply to chat ID. Logs Telegram's answer so problems are visible in Render logs."""
        if not self.token or "Example_" in self.token or not chat_id:
            print("[Telegram Bot ERROR] No token or chat_id - reply not sent")
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(url, json=payload)
                if r.status_code != 200:
                    print(f"[Telegram Bot ERROR] sendMessage {r.status_code}: {r.text}")
                    if reply_markup:  # retry without buttons so the user still gets an answer
                        payload.pop("reply_markup", None)
                        r2 = await client.post(url, json=payload)
                        print(f"[Telegram Bot] retry without buttons -> {r2.status_code}: {r2.text[:200]}")
                else:
                    print(f"[Telegram Bot] reply sent to {chat_id}")
        except Exception as e:
            print(f"[Telegram Bot ERROR] send failed: {e}")

# Global bot instance
bot_manager = TelegramBotManager()
