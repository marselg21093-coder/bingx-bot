from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import get_user
from ai.claude_api import ask_claude, SYSTEM_MENTOR
from handlers.common import check_limit, use_request, send_limit_exceeded, cancel
from handlers.keyboards import back_main_keyboard

MENTOR_Q = 0


async def mentor_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if not await check_limit(user_id):
        await send_limit_exceeded(update)
        return ConversationHandler.END

    await query.message.reply_text(
        "🧠 <b>AI-наставник</b>\n\n"
        "Задай любой вопрос о трейдинге:\n\n"
        "Например:\n"
        "• <i>Что такое ликвидность?</i>\n"
        "• <i>Как работает плечо?</i>\n"
        "• <i>Как не слить депозит?</i>\n"
        "• <i>Как вести дневник трейдера?</i>\n\n"
        "Или /cancel для выхода.",
        parse_mode="HTML",
    )
    return MENTOR_Q


async def mentor_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    question = update.message.text.strip()
    user_id = update.effective_user.id

    if not await check_limit(user_id):
        await send_limit_exceeded(update)
        return ConversationHandler.END

    await update.message.reply_text("🧠 Думаю над ответом...")

    user = await get_user(user_id)
    is_vip = bool(user and user["is_vip"])

    result = await ask_claude(SYSTEM_MENTOR, question, is_vip)
    await use_request(user_id)

    await update.message.reply_text(
        result,
        parse_mode="HTML",
        reply_markup=back_main_keyboard(),
    )
    # Stay in MENTOR_Q so user can ask more questions
    return MENTOR_Q
