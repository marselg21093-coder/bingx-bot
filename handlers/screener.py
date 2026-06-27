from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import get_user
from ai.claude_api import ask_claude, SYSTEM_SCREENER, DISCLAIMER
from handlers.common import check_limit, use_request, send_limit_exceeded, cancel
from handlers.keyboards import back_main_keyboard

SCREENER_INPUT = 0


async def screener_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if not await check_limit(user_id):
        await send_limit_exceeded(update)
        return ConversationHandler.END

    await query.message.reply_text(
        "🔍 <b>Поиск перспективных монет</b>\n\n"
        "⚠️ Это не торговые сигналы — только идеи для твоего анализа (DYOR).\n\n"
        "Опиши критерии для поиска. Например:\n\n"
        "<code>Ищу монеты:\n"
        "- Малая или средняя капитализация\n"
        "- Листинг на BingX\n"
        "- Упали на 50%+ от ATH\n"
        "- Сектор: AI или DeFi\n"
        "- Объём торгов не менее $5M в день</code>\n\n"
        "Или /cancel для отмены.",
        parse_mode="HTML",
    )
    return SCREENER_INPUT


async def screener_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    criteria = update.message.text.strip()
    user_id = update.effective_user.id

    await update.message.reply_text("🔍 Ищу идеи по твоим критериям...")

    user = await get_user(user_id)
    is_vip = bool(user and user["is_vip"])

    prompt = (
        "Пользователь ищет криптовалюты по следующим критериям:\n\n"
        f"{criteria}\n\n"
        "Предложи 5-7 монет для дальнейшего изучения. "
        "Для каждой укажи тикер, сектор, почему попала в список и ключевые риски."
    )

    result = await ask_claude(SYSTEM_SCREENER, prompt, is_vip)
    await use_request(user_id)

    await update.message.reply_text(
        result + DISCLAIMER,
        parse_mode="HTML",
        reply_markup=back_main_keyboard(),
    )
    return ConversationHandler.END
