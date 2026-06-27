from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import SBP_LINK


async def sbp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    text = (
        "🚀 <b>Пополнение BingX через СБП</b>\n\n"
        "Самый быстрый способ пополнить BingX рублями — без P2P!\n\n"
        "<b>Как это работает:</b>\n"
        "1. Переходишь на сервис по ссылке ниже\n"
        "2. Вводишь свой <b>UID</b> с BingX\n"
        "3. Указываешь сумму пополнения\n"
        "4. Оплачиваешь через СБП с любого банка\n"
        "5. USDT зачисляется на BingX за 1-5 минут\n\n"
        "<b>Преимущества:</b>\n"
        "✅ Быстрое зачисление\n"
        "✅ Не нужен P2P\n"
        "✅ Оплата с карты любого банка через СБП\n"
        "✅ Нет риска заморозки карты\n\n"
        "<b>Требования:</b>\n"
        "• Пройденный KYC на BingX\n"
        "• Знать свой UID (Профиль → UID)\n\n"
        "💡 Не знаешь свой UID? Нажми «🟦 BingX Assistant» → «Найти UID»"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Перейти к пополнению", url=SBP_LINK)],
        [InlineKeyboardButton("↩️ Главное меню", callback_data="back_main")],
    ])

    await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
