from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import get_user
from ai.claude_api import ask_claude, SYSTEM_PORTFOLIO, DISCLAIMER
from handlers.common import check_limit, use_request, send_limit_exceeded, cancel
from handlers.keyboards import back_main_keyboard

PORTFOLIO_INPUT = 0

EXAMPLE = (
    "<code>BTC 40%\n"
    "ETH 30%\n"
    "SOL 20%\n"
    "DOGE 10%</code>"
)


async def portfolio_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if not await check_limit(user_id):
        await send_limit_exceeded(update)
        return ConversationHandler.END

    await query.message.reply_text(
        f"💼 <b>Анализ портфеля</b>\n\n"
        f"Напиши список активов и их доли в портфеле.\n\n"
        f"Пример:\n{EXAMPLE}\n\n"
        f"Или /cancel для отмены.",
        parse_mode="HTML",
    )
    return PORTFOLIO_INPUT


async def portfolio_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    user_id = update.effective_user.id

    await update.message.reply_text("💼 Анализирую портфель...")

    user = await get_user(user_id)
    is_vip = bool(user and user["is_vip"])

    result = await ask_claude(SYSTEM_PORTFOLIO, f"Вот мой портфель:\n{text}", is_vip)
    await use_request(user_id)

    await update.message.reply_text(
        result + DISCLAIMER,
        parse_mode="HTML",
        reply_markup=back_main_keyboard(),
    )
    return ConversationHandler.END
