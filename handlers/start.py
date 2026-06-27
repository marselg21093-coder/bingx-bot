from telegram import Update
from telegram.ext import ContextTypes
from database import get_or_create_user
from handlers.keyboards import main_menu_keyboard

WELCOME = (
    "👋 <b>Привет, {name}!</b>\n\n"
    "Я <b>TokenRu AI Terminal</b> — AI-терминал для трейдера BingX 24/7\n\n"
    "Что умею:\n"
    "📊 Анализировать рынок и монеты\n"
    "⚖️ Считать риски и размер позиции\n"
    "🧠 Отвечать на вопросы по трейдингу\n"
    "📘 Обучать основам крипторынка\n"
    "📸 Анализировать твои сделки\n\n"
    "⚠️ <i>Бот не даёт торговых сигналов и не обещает прибыль. "
    "Только аналитика, обучение и риск-менеджмент.</i>\n\n"
    "Выбери раздел 👇"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await get_or_create_user(user.id, user.username or "", user.first_name or "")
    await update.message.reply_text(
        WELCOME.format(name=user.first_name or "трейдер"),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
