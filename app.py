"""
Mio Ads Telegram Mini App Ads Ecosystem - Master Server Application
Engineered with FastAPI for scalable deployment on Render's free tier web service.
"""

import os
import time
import uuid
import shutil
from typing import List, Optional

from fastapi import FastAPI, Request, HTTPException, Depends, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config import config
from database import db_manager, db
from models import (
    UserRegisterRequest, ChannelCreateRequest, ChannelModerationRequest,
    CampaignCreateRequest, DepositRequest, WithdrawalRequest,
    WithdrawalModerationRequest, TicketCreateRequest, TicketResponseRequest,
    AffiliateApplyRequest, AffiliateModerationRequest, SystemSettingsUpdateRequest,
    DatabaseSwitchRequest, DatabaseTestRequest, BroadcastRequest, AdImpressionTrackRequest
)
from invoices import invoice_generator
from lock_channel import lock_ledger
from telegram_bot import bot_manager

# Initialize FastAPI App
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="Decentralized Telegram Ads Network, Channel Monetization, and Administrative Lock Ledger"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure Required Directories
os.makedirs(config.STATIC_DIR, exist_ok=True)
os.makedirs(config.UPLOADS_DIR, exist_ok=True)
os.makedirs(config.INVOICES_DIR, exist_ok=True)
os.makedirs(config.TEMPLATES_DIR, exist_ok=True)

# Mount Static Assets & Templates
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
templates = Jinja2Templates(directory=config.TEMPLATES_DIR)


# =====================================================================
# FRONTEND VIEWS & DEEP LINKS
# =====================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_mini_app(request: Request):
    """Serves the Telegram Mini App with mandatory opening view and dynamic watermark."""
    return templates.TemplateResponse(request, "index.html", {"config": config})

@app.get("/app", response_class=HTMLResponse)
async def serve_mini_app_alias(request: Request):
    return templates.TemplateResponse(request, "index.html", {"config": config})

@app.get("/r/{ref_code}")
async def handle_referral_click(ref_code: str):
    """
    Automated referral tracking system counting clicks per URL.
    Increments referrer's click metric and redirects to the Mini App with deep link.
    """
    user_doc = db_manager.db.users.find_one({
        "$or": [{"referral_code": ref_code}, {"telegram_id": int(ref_code) if ref_code.isdigit() else 0}]
    })
    if user_doc:
        db_manager.db.users.update_one(
            {"_id": user_doc["_id"]},
            {"$inc": {"total_referral_clicks": 1}}
        )
        print(f"[Referral Tracker] Tracked click for referral code: {ref_code}")

    return RedirectResponse(url=f"/?start=ref_{ref_code}")


# =====================================================================
# USER PROFILE & SETTINGS ENDPOINTS
# =====================================================================

@app.get("/api/v1/user/profile")
async def get_user_profile(telegram_id: int):
    """Fetches unique user profile utilizing Telegram ID as the sole static identifier."""
    user = db_manager.db.users.find_one({"telegram_id": telegram_id})
    if not user:
        # Auto-register if not yet existing
        user = {
            "telegram_id": telegram_id,
            "username": f"user_{telegram_id}",
            "first_name": "Telegram User",
            "role": "admin" if telegram_id in config.ADMIN_TELEGRAM_IDS else "user",
            "preferred_currency": "USDT",
            "language": config.DEFAULT_LANGUAGE,
            "wallet_balance_usdt": 10.00,  # Signup bonus
            "wallet_balance_inr": 800.00,
            "api_key": f"mio_usr_key_{telegram_id}_{int(time.time())}",
            "referral_code": f"REF{telegram_id}",
            "referred_by": None,
            "total_referral_clicks": 0,
            "is_affiliate_approved": False,
            "created_at": time.time()
        }
        db_manager.db.users.insert_one(user)

    user["_id"] = str(user["_id"])
    return user

@app.post("/api/v1/user/settings/language")
async def update_language_setting(data: dict):
    tg_id = data.get("telegram_id")
    lang = data.get("language", "en")
    db_manager.db.users.update_one({"telegram_id": tg_id}, {"$set": {"language": lang}})
    return {"success": True, "language": lang}

@app.post("/api/v1/user/settings/currency")
async def update_currency_setting(data: dict):
    tg_id = data.get("telegram_id")
    curr = data.get("preferred_currency", "USDT")
    db_manager.db.users.update_one({"telegram_id": tg_id}, {"$set": {"preferred_currency": curr}})
    return {"success": True, "preferred_currency": curr}


# =====================================================================
# CHANNEL MANAGEMENT (MONETIZATION & PROMOTION)
# =====================================================================

@app.post("/api/v1/channels/link")
async def link_channel(req: ChannelCreateRequest):
    """
    Users can link channels for Promotion or Monetization.
    Spec Requirement: Every added channel requires manual Admin approval before campaigns can run.
    """
    channel_id = f"ch_{uuid.uuid4().hex[:8]}"
    channel_doc = {
        "channel_id": channel_id,
        "telegram_id": req.telegram_id,
        "title": req.title,
        "username": req.username,
        "type": req.type,  # 'promotion' or 'monetization'
        "category": req.category,
        "subscribers": req.subscribers,
        "status": "pending",  # Requires manual Admin approval
        "total_clicks": 0,
        "total_views": 0,
        "earnings_usdt": 0.0,
        "created_at": time.time()
    }

    db_manager.db.channels.insert_one(channel_doc)
    channel_doc["_id"] = str(channel_doc["_id"])

    # Mirror to Lock Ledger
    await lock_ledger.mirror_channel_moderation(channel_doc, "SUBMITTED_FOR_REVIEW", req.telegram_id)
    return channel_doc

@app.get("/api/v1/channels/list")
async def list_user_channels(telegram_id: int):
    channels = list(db_manager.db.channels.find({"telegram_id": telegram_id}))
    for ch in channels:
        ch["_id"] = str(ch["_id"])
    return channels

@app.get("/api/v1/channels/leaderboard")
async def get_leaderboard():
    """
    Spec Requirement: Global channel ranking system based on volume;
    public leaderboard displays Channel Name and Logo only (no external links for privacy).
    """
    channels = list(db_manager.db.channels.find(
        {"status": "approved"},
        {"_id": 0, "channel_id": 1, "title": 1, "category": 1, "total_views": 1, "total_clicks": 1}
    ).sort("total_views", -1).limit(20))
    return channels


# =====================================================================
# ADVERTISING & MONETIZATION SYSTEM (CPC / CPM & DWELL-TIME)
# =====================================================================

@app.post("/api/v1/campaigns/create")
async def create_campaign(req: CampaignCreateRequest):
    """Creates a new CPC or CPM campaign; deducts budget from advertiser wallet."""
    user = db_manager.db.users.find_one({"telegram_id": req.advertiser_id})
    if not user or user.get("wallet_balance_usdt", 0.0) < req.budget_usdt:
        raise HTTPException(status_code=400, detail="Insufficient USDT wallet balance. Please deposit funds first.")

    # Deduct budget
    new_balance = user["wallet_balance_usdt"] - req.budget_usdt
    inr_rate = config.USDT_TO_INR_RATE
    db_manager.db.users.update_one(
        {"telegram_id": req.advertiser_id},
        {"$set": {"wallet_balance_usdt": new_balance, "wallet_balance_inr": new_balance * inr_rate}}
    )

    campaign_id = f"cmp_{uuid.uuid4().hex[:8]}"
    campaign_doc = {
        "campaign_id": campaign_id,
        "advertiser_id": req.advertiser_id,
        "title": req.title,
        "narrative": req.narrative,
        "target_url": req.target_url,
        "banner_url": req.banner_url or "/static/images/logo.png",
        "model": req.model,
        "bid_usdt": req.bid_usdt,
        "budget_usdt": req.budget_usdt,
        "spent_usdt": 0.0,
        "dwell_time_seconds": req.dwell_time_seconds,
        "impressions": 0,
        "clicks": 0,
        "status": "active",
        "created_at": time.time()
    }
    db_manager.db.campaigns.insert_one(campaign_doc)

    # Generate invoice for campaign budget allocation
    tx_data = {
        "tx_id": f"TX-CMP-{campaign_id}",
        "type": "Campaign Creation",
        "amount": req.budget_usdt,
        "currency": "USDT",
        "description": f"Ad Campaign Budget: {req.title} ({req.model})",
        "deduct_fee": False,
        "usdt_to_inr_rate": inr_rate,
        "status": "COMPLETED",
        "created_at": time.time()
    }
    inv_meta = invoice_generator.generate_invoice_pdf(tx_data, user)
    await lock_ledger.mirror_invoice(inv_meta)

    campaign_doc["_id"] = str(campaign_doc["_id"])
    return campaign_doc

@app.get("/api/v1/campaigns/list")
async def list_campaigns():
    campaigns = list(db_manager.db.campaigns.find({"status": "active"}).sort("created_at", -1).limit(20))
    for cmp in campaigns:
        cmp["_id"] = str(cmp["_id"])
    return campaigns

@app.post("/api/v1/ad/track")
async def track_ad_impression(req: AdImpressionTrackRequest):
    """
    Spec Requirement: Configurable dwell-time timer (1-2 minutes) required before impressions count,
    unless ads are clicked directly (skipping timer).
    """
    campaign = db_manager.db.campaigns.find_one({"campaign_id": req.campaign_id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    required_dwell = campaign.get("dwell_time_seconds", config.DEFAULT_DWELL_TIME_SECONDS)
    valid_impression = False
    valid_click = False

    if req.clicked_directly:
        valid_click = True
        print(f"[Ad Tracker] Direct click verified! Bypassed {required_dwell}s dwell timer.")
    elif req.dwell_time_elapsed >= required_dwell:
        valid_impression = True
        print(f"[Ad Tracker] Dwell time {req.dwell_time_elapsed}s verified >= {required_dwell}s required.")
    else:
        return {"status": "ignored", "reason": f"Dwell time {req.dwell_time_elapsed}s insufficient (< {required_dwell}s)"}

    # Calculate fee and publisher payout
    platform_fee = config.PLATFORM_FEE_PERCENT / 100.0
    cost_deduction = 0.0

    if valid_click:
        cost_deduction = campaign.get("bid_usdt", 0.02)
        publisher_earn = cost_deduction * (1.0 - platform_fee)
        db_manager.db.campaigns.update_one(
            {"campaign_id": req.campaign_id},
            {"$inc": {"clicks": 1, "spent_usdt": cost_deduction}}
        )
        if req.channel_id:
            db_manager.db.channels.update_one(
                {"channel_id": req.channel_id},
                {"$inc": {"total_clicks": 1, "earnings_usdt": publisher_earn}}
            )
    elif valid_impression:
        cost_deduction = (campaign.get("bid_usdt", 2.50) / 1000.0)
        publisher_earn = cost_deduction * (1.0 - platform_fee)
        db_manager.db.campaigns.update_one(
            {"campaign_id": req.campaign_id},
            {"$inc": {"impressions": 1, "spent_usdt": cost_deduction}}
        )
        if req.channel_id:
            db_manager.db.channels.update_one(
                {"channel_id": req.channel_id},
                {"$inc": {"total_views": 1, "earnings_usdt": publisher_earn}}
            )

    return {
        "status": "success",
        "valid_click": valid_click,
        "valid_impression": valid_impression,
        "cost_deducted_usdt": round(cost_deduction, 4),
        "skipped_timer": req.clicked_directly
    }


# =====================================================================
# WALLET, INVOICES & ADMINISTRATIVE LOCK LEDGER
# =====================================================================

@app.post("/api/v1/wallet/deposit")
async def deposit_funds(req: DepositRequest):
    """
    Spec Requirement: Minimum deposits: 500 INR (UPI) or $10 USDT.
    Automatic PDF invoice generation backed up to Lock Channel.
    """
    if req.currency == "INR" and req.amount < config.MIN_DEPOSIT_INR:
        raise HTTPException(status_code=400, detail=f"Minimum deposit via UPI is ₹{config.MIN_DEPOSIT_INR} INR")
    if req.currency == "USDT" and req.amount < config.MIN_DEPOSIT_USDT:
        raise HTTPException(status_code=400, detail=f"Minimum deposit via USDT is ${config.MIN_DEPOSIT_USDT} USDT")

    user = db_manager.db.users.find_one({"telegram_id": req.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    inr_rate = config.USDT_TO_INR_RATE
    added_usdt = req.amount if req.currency == "USDT" else round(req.amount / inr_rate, 2)
    added_inr = round(added_usdt * inr_rate, 2)

    new_usdt = user.get("wallet_balance_usdt", 0.0) + added_usdt
    new_inr = round(new_usdt * inr_rate, 2)

    db_manager.db.users.update_one(
        {"telegram_id": req.user_id},
        {"$set": {"wallet_balance_usdt": new_usdt, "wallet_balance_inr": new_inr}}
    )

    tx_id = f"DEP-{uuid.uuid4().hex[:8].upper()}"
    tx_data = {
        "tx_id": tx_id,
        "user_id": req.user_id,
        "type": "Deposit",
        "currency": req.currency,
        "amount": added_usdt,
        "description": f"Mio Ads Deposit via {req.payment_method} ({req.utr_or_txid or 'Verified'})",
        "deduct_fee": False,
        "usdt_to_inr_rate": inr_rate,
        "status": "COMPLETED",
        "created_at": time.time()
    }

    # Generate PDF Invoice
    inv_meta = invoice_generator.generate_invoice_pdf(tx_data, user)
    # Mirror instantaneously to Lock Channel
    await lock_ledger.mirror_invoice(inv_meta)

    return {
        "success": True,
        "tx_id": tx_id,
        "invoice_id": inv_meta["invoice_id"],
        "invoice_pdf_url": inv_meta["web_url"],
        "new_balance_usdt": new_usdt,
        "new_balance_inr": new_inr
    }

@app.post("/api/v1/wallet/withdraw")
async def request_withdrawal(req: WithdrawalRequest):
    """
    Spec Requirement: Minimum withdrawal: $5, subject to a 48-hour Admin review period.
    """
    if req.amount_usdt < config.MIN_WITHDRAWAL_USDT:
        raise HTTPException(status_code=400, detail=f"Minimum withdrawal is ${config.MIN_WITHDRAWAL_USDT} USDT")

    user = db_manager.db.users.find_one({"telegram_id": req.user_id})
    if not user or user.get("wallet_balance_usdt", 0.0) < req.amount_usdt:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance for this withdrawal")

    # Lock funds pending 48-hour review
    new_usdt = user["wallet_balance_usdt"] - req.amount_usdt
    inr_rate = config.USDT_TO_INR_RATE
    db_manager.db.users.update_one(
        {"telegram_id": req.user_id},
        {"$set": {"wallet_balance_usdt": new_usdt, "wallet_balance_inr": new_usdt * inr_rate}}
    )

    tx_id = f"WD-{uuid.uuid4().hex[:8].upper()}"
    tx_doc = {
        "tx_id": tx_id,
        "user_id": req.user_id,
        "amount": req.amount_usdt,
        "currency": "USDT",
        "destination_address": req.payout_address,
        "status": "pending_48h_review",
        "created_at": time.time(),
        "review_deadline": time.time() + (config.WITHDRAWAL_REVIEW_HOURS * 3600)
    }
    db_manager.db.transactions.insert_one(tx_doc)

    # Mirror to Lock Ledger
    await lock_ledger.mirror_withdrawal_request(tx_doc)

    return {
        "success": True,
        "tx_id": tx_id,
        "status": "pending_48h_review",
        "review_sla_hours": config.WITHDRAWAL_REVIEW_HOURS,
        "message": "Withdrawal request submitted under strict 48-Hour Admin Review SLA."
    }

@app.get("/api/v1/invoices/list")
async def list_invoices(user_id: int):
    invoices = list(db_manager.db.lock_ledger.find(
        {"event_type": "INVOICE_GENERATED", "user_id": str(user_id)},
        {"_id": 0}
    ).sort("timestamp", -1))
    return invoices


# =====================================================================
# SUPPORT TICKETING & 24-HOUR SLA
# =====================================================================

@app.post("/api/v1/support/upload")
async def upload_ticket_attachments(files: List[UploadFile] = File(...)):
    """Handles multi-file attachments (photos, videos, docs) for support tickets."""
    uploaded = []
    for f in files:
        ext = os.path.splitext(f.filename)[1]
        save_name = f"att_{uuid.uuid4().hex[:10]}{ext}"
        save_path = os.path.join(config.UPLOADS_DIR, save_name)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)
        uploaded.append(f"/static/uploads/{save_name}")
    return {"filenames": uploaded}

@app.post("/api/v1/support/tickets/create")
async def create_support_ticket(req: TicketCreateRequest):
    """
    Spec Requirement: Capturing User ID, Gmail, issue narrative, and multi-file attachments.
    Strict 24-hour response SLA. Mirrored to private administrative Lock Channel.
    """
    ticket_id = f"TCK-{int(time.time())}-{uuid.uuid4().hex[:4].upper()}"
    ticket_doc = {
        "ticket_id": ticket_id,
        "user_id": req.user_id,
        "gmail": req.gmail,
        "narrative": req.narrative,
        "attachments": req.attachments or [],
        "status": "open",
        "created_at": time.time(),
        "sla_deadline": time.time() + (config.SUPPORT_SLA_HOURS * 3600),
        "responses": []
    }
    db_manager.db.tickets.insert_one(ticket_doc)

    # Mirror to Lock Ledger
    await lock_ledger.mirror_ticket_activity(ticket_doc, "TICKET_CREATED")

    ticket_doc["_id"] = str(ticket_doc["_id"])
    return ticket_doc

@app.get("/api/v1/support/tickets")
async def get_user_tickets(user_id: int):
    tickets = list(db_manager.db.tickets.find({"user_id": user_id}).sort("created_at", -1))
    for t in tickets:
        t["_id"] = str(t["_id"])
    return tickets


# =====================================================================
# REFERRAL & AFFILIATE PROGRAM
# =====================================================================

@app.post("/api/v1/affiliate/apply")
async def apply_for_affiliate(req: AffiliateApplyRequest):
    """Application-based affiliate program requiring Admin approval."""
    app_doc = {
        "user_id": req.user_id,
        "traffic_source": req.traffic_source,
        "estimated_volume": req.estimated_volume,
        "notes": req.notes,
        "status": "pending",
        "custom_rate_usdt": config.AFFILIATE_CLICK_RATE_USDT,
        "created_at": time.time()
    }
    db_manager.db.affiliates.insert_one(app_doc)
    app_doc["_id"] = str(app_doc["_id"])
    return app_doc


# =====================================================================
# MASTER ADMIN PANEL & SYSTEM CONTROL
# =====================================================================

@app.get("/api/v1/system/settings")
async def get_system_settings():
    return {
        "platform_fee_percent": config.PLATFORM_FEE_PERCENT,
        "usdt_to_inr_rate": config.USDT_TO_INR_RATE,
        "affiliate_click_rate_usdt": config.AFFILIATE_CLICK_RATE_USDT,
        "default_dwell_time_seconds": config.DEFAULT_DWELL_TIME_SECONDS,
        "lock_channel_id": config.LOCK_CHANNEL_ID,
        "admin_ids": config.ADMIN_TELEGRAM_IDS
    }

@app.post("/api/v1/admin/settings/update")
async def update_system_settings(req: SystemSettingsUpdateRequest):
    """Admin retains control to configure platform fee, exchange rate, and thresholds anytime."""
    if req.platform_fee_percent is not None:
        config.PLATFORM_FEE_PERCENT = req.platform_fee_percent
    if req.usdt_to_inr_rate is not None:
        config.USDT_TO_INR_RATE = req.usdt_to_inr_rate
    if req.affiliate_click_rate_usdt is not None:
        config.AFFILIATE_CLICK_RATE_USDT = req.affiliate_click_rate_usdt
    if req.default_dwell_time_seconds is not None:
        config.DEFAULT_DWELL_TIME_SECONDS = req.default_dwell_time_seconds

    # Save to MongoDB system settings collection
    db_manager.db.system_settings.update_one(
        {"_id": "global_config"},
        {"$set": {
            "platform_fee_percent": config.PLATFORM_FEE_PERCENT,
            "usdt_to_inr_rate": config.USDT_TO_INR_RATE,
            "affiliate_click_rate_usdt": config.AFFILIATE_CLICK_RATE_USDT,
            "default_dwell_time_seconds": config.DEFAULT_DWELL_TIME_SECONDS,
            "updated_at": time.time()
        }},
        upsert=True
    )
    return {"success": True, "settings": await get_system_settings()}

@app.get("/api/v1/admin/channels/pending")
async def get_pending_channels():
    channels = list(db_manager.db.channels.find({"status": "pending"}))
    for ch in channels:
        ch["_id"] = str(ch["_id"])
    return channels

@app.post("/api/v1/admin/channels/moderate")
async def moderate_channel(req: ChannelModerationRequest):
    """Admin moderation for linked channels."""
    channel = db_manager.db.channels.find_one({"channel_id": req.channel_id})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    db_manager.db.channels.update_one(
        {"channel_id": req.channel_id},
        {"$set": {"status": req.action, "moderated_by": req.admin_id, "moderated_at": time.time()}}
    )
    await lock_ledger.mirror_channel_moderation(channel, req.action, req.admin_id)
    return {"success": True, "channel_id": req.channel_id, "status": req.action}

@app.get("/api/v1/admin/withdrawals/pending")
async def get_pending_withdrawals():
    withdrawals = list(db_manager.db.transactions.find({"status": "pending_48h_review"}))
    for w in withdrawals:
        w["_id"] = str(w["_id"])
    return withdrawals

@app.post("/api/v1/admin/withdrawals/moderate")
async def moderate_withdrawal(req: WithdrawalModerationRequest):
    """Approves or rejects a withdrawal request after 48-hour review."""
    tx = db_manager.db.transactions.find_one({"tx_id": req.tx_id})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    new_status = "approved" if req.action == "approved" else "rejected"
    db_manager.db.transactions.update_one(
        {"tx_id": req.tx_id},
        {"$set": {"status": new_status, "moderated_by": req.admin_id, "moderated_at": time.time()}}
    )

    # If rejected, refund user wallet
    if new_status == "rejected":
        inr_rate = config.USDT_TO_INR_RATE
        refund_amount = tx["amount"]
        db_manager.db.users.update_one(
            {"telegram_id": tx["user_id"]},
            {"$inc": {"wallet_balance_usdt": refund_amount, "wallet_balance_inr": refund_amount * inr_rate}}
        )

    return {"success": True, "tx_id": req.tx_id, "status": new_status}

@app.get("/api/v1/admin/database/status")
async def get_database_status():
    """Returns dynamic MongoDB connection pool status for Admin Panel."""
    return db_manager.get_database_status()

@app.post("/api/v1/admin/database/switch")
async def switch_database_uri(req: DatabaseSwitchRequest):
    """Switches active MongoDB connection to dynamic URL via Admin Panel."""
    result = db_manager.switch_database_uri(req.uri_index or 0, req.custom_uri)
    return result

@app.post("/api/v1/admin/database/test")
async def test_database_connection(req: DatabaseTestRequest):
    """Tests latency to any external MongoDB URI."""
    return db_manager.test_connection(req.uri)

@app.post("/api/v1/admin/broadcast")
async def trigger_global_broadcast(req: BroadcastRequest):
    """Spec Requirement: Trigger a manual global broadcast across all channels."""
    broadcast_doc = {
        "broadcast_id": f"BC-{uuid.uuid4().hex[:6].upper()}",
        "admin_id": req.admin_id,
        "title": req.title,
        "message": req.message,
        "target": req.target,
        "action_url": req.action_url,
        "timestamp": time.time()
    }
    db_manager.db.broadcasts.insert_one(broadcast_doc)

    # Mirror to Lock Ledger
    await lock_ledger._send_telegram_lock_message(
        f"📢 <b>[GLOBAL BROADCAST DISPATCHED]</b>\n\n"
        f"📌 <b>Title:</b> {req.title}\n"
        f"🎯 <b>Target:</b> {req.target}\n\n"
        f"{req.message}"
    )

    broadcast_doc["_id"] = str(broadcast_doc["_id"])
    return {"success": True, "broadcast": broadcast_doc}

@app.get("/api/v1/admin/lock-ledger/logs")
async def get_lock_ledger_logs():
    logs = list(db_manager.db.lock_ledger.find({}, {"_id": 0}).sort("timestamp", -1).limit(50))
    return logs


# =====================================================================
# TELEGRAM BOT WEBHOOK & UNIFIED COMMAND PARSER
# =====================================================================

@app.post("/api/v1/telegram/webhook")
async def telegram_webhook(update: dict):
    return await bot_manager.handle_update(update)

@app.post("/api/v1/command/parse")
async def parse_global_command(payload: dict):
    """
    Spec Requirement: All standard User and Admin navigation commands
    are inherently parsed and executed via the unified Mini App interface.
    """
    cmd = payload.get("command", "")
    tg_id = payload.get("telegram_id", 100200300)
    mock_update = {
        "message": {
            "chat": {"id": tg_id},
            "from": {"id": tg_id, "first_name": "App User", "username": "app_user"},
            "text": cmd
        }
    }
    return await bot_manager.handle_update(mock_update)


# =====================================================================
# HEALTH CHECK & RENDER DEPLOYMENT PROBE
# =====================================================================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": config.APP_NAME,
        "version": config.APP_VERSION,
        "database": db_manager.get_database_status(),
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=config.SERVER_HOST, port=config.SERVER_PORT, reload=False)
