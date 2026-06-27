from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import CHANNEL_LINK


async def vip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    text = (
        "💎 <b>VIP-доступ — TokenRu AI Terminal</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🆓 <b>Бесплатный план</b>\n"
        "• 5 AI-запросов в день\n"
        "• Все разделы бота\n"
        "• 10 уроков и тесты\n"
        "• Модель: Claude Haiku (быстрая)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💎 <b>VIP план</b>\n"
        "• ♾️ Безлимитные AI-запросы\n"
        "• Улучшенная модель Claude Sonnet\n"
        "• Более глубокий и точный анализ\n"
        "• Приоритетная поддержка\n"
        "• Все функции без ограничений\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💬 <b>Как получить VIP:</b>\n"
        "Напиши в наш Telegram-канал или администратору.\n"
        "VIP выдаётся вручную после оплаты."
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Написать администратору", url=CHANNEL_LINK)],
        [InlineKeyboardButton("↩️ Главное меню", callback_data="back_main")],
    ])

    await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
