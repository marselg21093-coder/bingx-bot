import requests
from telegram import Update
from telegram.ext import ContextTypes
from database import get_user
from ai.claude_api import ask_claude, SYSTEM_MARKET, DISCLAIMER
from handlers.common import check_limit, use_request, send_limit_exceeded
from handlers.keyboards import back_main_keyboard


def get_prices() -> str:
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin,ethereum", "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=8,
        )
        d = r.json()
        btc = d["bitcoin"]["usd"]
        btc_c = d["bitcoin"]["usd_24h_change"]
        eth = d["ethereum"]["usd"]
        eth_c = d["ethereum"]["usd_24h_change"]
        return (
            f"Текущие цены: BTC ${btc:,.0f} ({btc_c:+.1f}% за 24ч), "
            f"ETH ${eth:,.0f} ({eth_c:+.1f}% за 24ч)"
        )
    except Exception:
        return "Данные о ценах временно недоступны"


async def market_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if not await check_limit(user_id):
        await send_limit_exceeded(update)
        return

    await query.message.reply_text("📊 Анализирую рынок, подожди...")

    user = await get_user(user_id)
    is_vip = bool(user and user["is_vip"])
    prices = get_prices()
    prompt = f"{prices}\n\nСделай полный обзор крипторынка прямо сейчас."

    result = await ask_claude(SYSTEM_MARKET, prompt, is_vip)
    await use_request(user_id)

    await query.message.reply_text(
        result + DISCLAIMER,
        parse_mode="HTML",
        reply_markup=back_main_keyboard(),
    )
