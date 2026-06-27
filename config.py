import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN      = os.environ["BOT_TOKEN"]
CLAUDE_API_KEY = os.environ["CLAUDE_API_KEY"]
ADMIN_IDS      = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]

FREE_DAILY_LIMIT = 5
FREE_MODEL       = "claude-haiku-4-5-20251001"
VIP_MODEL        = "claude-sonnet-4-6"

DB_PATH      = "tokenru.db"
REF_LINK     = "https://bingx.com/ru/partner/A888"
SBP_LINK     = "https://sbppaybingx.ru/register?ref=BINGX"
CHANNEL_LINK = "https://t.me/tokenruru"
