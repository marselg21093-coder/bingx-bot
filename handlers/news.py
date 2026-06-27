from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import get_user
from ai.claude_api import ask_claude, SYSTEM_NEWS, DISCLAIMER
from handlers.common import check_limit, use_request, send_limit_exceeded, cancel
from handlers.keyboards import back_main_keyboard

NEWS_INPUT = 0


async def news_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if not await check_limit(user_id):
        await send_limit_exceeded(update)
        return ConversationHandler.END

    await query.message.reply_text(
        "📰 <b>Разбор новостей</b>\n\n"
        "Вставь текст новости или её краткое содержание.\n"
        "Я объясню, что это значит для рынка.\n\n"
        "Или /cancel для отмены.",
        parse_mode="HTML",
    )
    return NEWS_INPUT


async def news_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    news_text = update.message.text.strip()
    user_id = update.effective_user.id

    await update.message.reply_text("📰 Анализирую новость...")

    user = await get_user(user_id)
    is_vip = bool(user and user["is_vip"])

    result = await ask_claude(SYSTEM_NEWS, f"Новость:\n\n{news_text}", is_vip)
    await use_request(user_id)

    await update.message.reply_text(
        result + DISCLAIMER,
        parse_mode="HTML",
        reply_markup=back_main_keyboard(),
    )
    return ConversationHandler.END
