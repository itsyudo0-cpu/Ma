"""
Mio Ads Telegram Mini App Ads Ecosystem - Local Configuration Module
Strictly encapsulates all dynamic variables, API keys, operational values,
and thresholds locally without requiring remote environment variable injection.
"""

from typing import List, Dict, Any
import os

class Config:
    # Application & Server Info
    APP_NAME: str = "Mio Ads"
    APP_VERSION: str = "2.0.0"
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = int(os.environ.get("PORT", 8080))
    BASE_URL: str = "https://ma-ofmm.onrender.com"

    # Telegram Bot & Mini App
    TELEGRAM_BOT_TOKEN: str = "9288636276:AAHppMVE_ghxA-jDw-6ElhMhfcwuAaSDZdQ"
    TELEGRAM_BOT_NAME: str = "mioads bot"
    TELEGRAM_BOT_USERNAME: str = "mioadsbot"
    TELEGRAM_CHANNEL_NAME: str = "Mioads"
    TELEGRAM_CHANNEL_USERNAME: str = "@mioads"
    MINI_APP_SHORT_NAME: str = "MA"

    # Administrative 'Lock Channel' (Private channel for security mirrors, logs, SLA alerts, invoices)
    LOCK_CHANNEL_ID: str = "-1004466373562"
    LOCK_CHANNEL_TITLE: str = "Mio Ads [Administrative Lock Ledger]"

    # MongoDB Dynamic Configuration
    # Supports primary connection string and additional fallback/secondary URIs
    # Default URL (used the first time). Admin can add/remove more URLs from the Admin Panel.
    MONGODB_PRIMARY_URI: str = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/mioads_db")
    DB_URLS_FILE: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "db_urls.json")
    DB_NAME: str = "mioads_db"

    # Platform Financial & Operational Thresholds
    PLATFORM_FEE_PERCENT: float = 30.0         # Dynamic platform fee deduction (%)
    USDT_TO_INR_RATE: float = 80.0             # Default $1 = 80 INR (adjustable by Admin)
    MIN_DEPOSIT_INR: float = 500.0             # Minimum 500 INR via UPI
    MIN_DEPOSIT_USDT: float = 10.0             # Minimum $10 USDT
    MIN_WITHDRAWAL_USDT: float = 5.0           # Minimum $5 USDT withdrawal
    WITHDRAWAL_REVIEW_HOURS: int = 48          # Strict 48-hour Admin review period
    SUPPORT_SLA_HOURS: int = 24                # Strict 24-hour response SLA

    # Advertising & Traffic Logic
    DEFAULT_CPC_RATE_USDT: float = 0.01        # CPC default per click
    DEFAULT_CPM_RATE_USDT: float = 2.50        # CPM per 1000 impressions
    AFFILIATE_CLICK_RATE_USDT: float = 0.005   # Configurable affiliate per-click rate ($0.005)
    DWELL_TIME_MIN_SECONDS: int = 60           # Dwell time timer minimum (1 minute)
    DWELL_TIME_MAX_SECONDS: int = 120          # Dwell time timer maximum (2 minutes)
    DEFAULT_DWELL_TIME_SECONDS: int = 60       # Configurable dwell-time required before impression counts

    # Admin access
    # Optional pre-approved admin Telegram IDs (leave empty: first admin is created by token login)
    ADMIN_TELEGRAM_IDS: List[int] = []
    # Admin login token. SET THIS (or env ADMIN_TOKEN) before deploying.
    ADMIN_TOKEN_PLACEHOLDER: str = "CHANGE_THIS_ADMIN_TOKEN"
    ADMIN_TOKEN: str = os.environ.get("ADMIN_TOKEN", "Kx9mP2vQ7rT4wZ8nB5cL1hJ6dF3sA0yE")
    ADMIN_SESSION_HOURS: int = 12

    # Localization Defaults
    DEFAULT_LANGUAGE: str = "en"
    SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
        # Indian Regional Languages
        "hi": {"name": "हिन्दी (Hindi)", "flag": "🇮🇳", "region": "India"},
        "bn": {"name": "বাংলা (Bengali)", "flag": "🇮🇳", "region": "India"},
        "ta": {"name": "தமிழ் (Tamil)", "flag": "🇮🇳", "region": "India"},
        "te": {"name": "తెలుగు (Telugu)", "flag": "🇮🇳", "region": "India"},
        "mr": {"name": "मराठी (Marathi)", "flag": "🇮🇳", "region": "India"},
        "gu": {"name": "ગુજરાતી (Gujarati)", "flag": "🇮🇳", "region": "India"},
        "kn": {"name": "ಕನ್ನಡ (Kannada)", "flag": "🇮🇳", "region": "India"},
        "ml": {"name": "മലയാളം (Malayalam)", "flag": "🇮🇳", "region": "India"},
        "pa": {"name": "ਪੰਜਾਬੀ (Punjabi)", "flag": "🇮🇳", "region": "India"},
        # Global Standards
        "en": {"name": "English", "flag": "🇺🇸", "region": "Global"},
        "ru": {"name": "Русский (Russian)", "flag": "🇷🇺", "region": "Global"},
        "ja": {"name": "日本語 (Japanese)", "flag": "🇯🇵", "region": "Global"},
        "zh": {"name": "中文 (Chinese)", "flag": "🇨🇳", "region": "Global"},
        "ko": {"name": "한국어 (Korean)", "flag": "🇰🇷", "region": "Global"},
        "es": {"name": "Español (Spanish)", "flag": "🇪🇸", "region": "Global"},
        "ar": {"name": "العربية (Arabic)", "flag": "🇦🇪", "region": "Global"}
    }

    # Supported Currencies
    SUPPORTED_CURRENCIES: Dict[str, str] = {
        "USDT": "Tether USD (USDT)",
        "INR": "Indian Rupee (₹)",
        "RUB": "Russian Ruble (₽)",
        "USD": "US Dollar ($)"
    }

    # Paths
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    STATIC_DIR: str = os.path.join(BASE_DIR, "static")
    TEMPLATES_DIR: str = os.path.join(BASE_DIR, "templates")
    UPLOADS_DIR: str = os.path.join(STATIC_DIR, "uploads")
    INVOICES_DIR: str = os.path.join(STATIC_DIR, "invoices")

# Singleton instance
config = Config()
