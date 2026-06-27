from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import get_user
from ai.claude_api import ask_claude, SYSTEM_COIN, DISCLAIMER
from handlers.common import check_limit, use_request, send_limit_exceeded, cancel
from handlers.keyboards import back_main_keyboard

COIN_TICKER = 0


async def coin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if not await check_limit(user_id):
        await send_limit_exceeded(update)
        return ConversationHandler.END

    await query.message.reply_text(
        "🪙 <b>Анализ монеты</b>\n\n"
        "Введи тикер монеты, например:\n"
        "<code>BTC</code>, <code>ETH</code>, <code>SOL</code>, <code>BNB</code>\n\n"
        "Или /cancel для отмены.",
        parse_mode="HTML",
    )
    return COIN_TICKER


async def coin_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ticker = update.message.text.strip().upper()
    user_id = update.effective_user.id

    if len(ticker) > 10 or not ticker.isalnum():
        await update.message.reply_text("⚠️ Введи корректный тикер, например BTC или ETH.")
        return COIN_TICKER

    await update.message.reply_text(f"🔍 Анализирую {ticker}, подожди...")

    user = await get_user(user_id)
    is_vip = bool(user and user["is_vip"])

    result = await ask_claude(SYSTEM_COIN, f"Проанализируй монету {ticker}.", is_vip)
    await use_request(user_id)

    await update.message.reply_text(
        result + DISCLAIMER,
        parse_mode="HTML",
        reply_markup=back_main_keyboard(),
    )
    return ConversationHandler.END
