from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from database import can_make_request, increment_requests, get_requests_left
from config import FREE_DAILY_LIMIT


LIMIT_TEXT = (
    "⛔️ <b>Лимит запросов исчерпан</b>\n\n"
    f"Бесплатный план: {FREE_DAILY_LIMIT} AI-запросов в день.\n"
    "Лимит сбросится в полночь.\n\n"
    "💎 Хочешь без ограничений? Нажми <b>«💎 VIP-доступ»</b> в главном меню."
)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Universal /cancel handler — exits any conversation."""
    context.user_data.clear()
    from handlers.keyboards import main_menu_keyboard
    await update.message.reply_text(
        "↩️ Отменено. Возвращаемся в главное меню.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback for 'back to main menu' button."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    from handlers.keyboards import main_menu_keyboard
    await query.message.edit_text(
        "🏠 Главное меню:",
        reply_markup=main_menu_keyboard(),
    )


async def check_limit(user_id: int) -> bool:
    """Returns True if user can make a request."""
    return await can_make_request(user_id)


async def use_request(user_id: int) -> None:
    """Increment request counter."""
    await increment_requests(user_id)


def back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("↩️ Главное меню", callback_data="back_main")
    ]])


async def send_limit_exceeded(update: Update) -> None:
    """Send limit exceeded message."""
    if update.callback_query:
        await update.callback_query.message.reply_text(
            LIMIT_TEXT, parse_mode="HTML", reply_markup=back_button()
        )
    elif update.message:
        await update.message.reply_text(
            LIMIT_TEXT, parse_mode="HTML", reply_markup=back_button()
        )
