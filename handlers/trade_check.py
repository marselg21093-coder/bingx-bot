from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, filters
from database import get_user
from ai.claude_api import ask_claude, ask_claude_with_image, SYSTEM_TRADE, DISCLAIMER
from handlers.common import check_limit, use_request, send_limit_exceeded, cancel
from handlers.keyboards import back_main_keyboard

TRADE_PHOTO, TRADE_DETAILS = range(2)

DETAILS_PROMPT = (
    "📝 <b>Опиши параметры сделки:</b>\n\n"
    "Отправь одним сообщением в таком формате:\n\n"
    "<code>Актив: BTC\n"
    "Направление: лонг\n"
    "Вход: 60000\n"
    "Стоп-лосс: 58000\n"
    "Тейк-профит: 65000\n"
    "Депозит: 1000$\n"
    "Размер риска: 2%</code>\n\n"
    "Или /cancel для отмены."
)


async def trade_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if not await check_limit(user_id):
        await send_limit_exceeded(update)
        return ConversationHandler.END

    await query.message.reply_text(
        "📸 <b>Проверка сделки</b>\n\n"
        "Пришли скриншот графика или сделки.\n"
        "Или напиши /skip, если хочешь анализ только по параметрам.",
        parse_mode="HTML",
    )
    return TRADE_PHOTO


async def trade_photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_data = await file.download_as_bytearray()
    context.user_data["trade_image"] = bytes(image_data)
    await update.message.reply_text(DETAILS_PROMPT, parse_mode="HTML")
    return TRADE_DETAILS


async def trade_skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["trade_image"] = None
    await update.message.reply_text(DETAILS_PROMPT, parse_mode="HTML")
    return TRADE_DETAILS


async def trade_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    details = update.message.text.strip()
    user_id = update.effective_user.id
    image_data = context.user_data.get("trade_image")

    await update.message.reply_text("🔍 Анализирую сделку...")

    user = await get_user(user_id)
    is_vip = bool(user and user["is_vip"])

    prompt = f"Проанализируй сделку по следующим параметрам:\n\n{details}"

    if image_data:
        result = await ask_claude_with_image(SYSTEM_TRADE, prompt, image_data, is_vip=is_vip)
    else:
        result = await ask_claude(SYSTEM_TRADE, prompt, is_vip)

    await use_request(user_id)
    context.user_data.clear()

    await update.message.reply_text(
        result + DISCLAIMER,
        parse_mode="HTML",
        reply_markup=back_main_keyboard(),
    )
    return ConversationHandler.END
