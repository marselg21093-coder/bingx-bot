from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from database import get_user, set_bingx_uid, get_requests_left
from config import FREE_DAILY_LIMIT
from handlers.keyboards import back_main_keyboard
import datetime

PROFILE_UID = 0


def profile_keyboard(has_uid: bool) -> InlineKeyboardMarkup:
    uid_label = "✏️ Изменить UID" if has_uid else "🔑 Указать BingX UID"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(uid_label, callback_data="profile_set_uid")],
        [InlineKeyboardButton("↩️ Главное меню", callback_data="back_main")],
    ])


async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    user = await get_user(user_id)
    if not user:
        await query.message.edit_text("⚠️ Профиль не найден. Напиши /start")
        return

    requests_left = await get_requests_left(user_id)
    vip_status = "💎 VIP" if user["is_vip"] else "🆓 Бесплатный"

    if requests_left == -1:
        req_line = "♾️ Безлимитный (VIP)"
    else:
        req_line = f"{requests_left} из {FREE_DAILY_LIMIT} осталось сегодня"

    reg_date = user["registered_at"][:10] if user["registered_at"] else "—"
    username = f"@{user['username']}" if user["username"] else "—"
    uid = user["bingx_uid"] or "Не указан"

    text = (
        f"👤 <b>Мой профиль</b>\n\n"
        f"🆔 Telegram ID: <code>{user_id}</code>\n"
        f"👤 Username: {username}\n"
        f"📅 Дата регистрации: {reg_date}\n\n"
        f"📊 Статус: <b>{vip_status}</b>\n"
        f"🔢 Запросы: {req_line}\n"
        f"📈 Всего запросов: {user['total_requests']}\n\n"
        f"🔑 BingX UID: <code>{uid}</code>"
    )

    await query.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=profile_keyboard(bool(user["bingx_uid"])),
    )


async def profile_set_uid_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "🔑 Введи свой BingX UID.\n\n"
        "Найти его можно в приложении BingX:\n"
        "Профиль → UID: XXXXXXXXXX\n\n"
        "Или /cancel для отмены."
    )
    return PROFILE_UID


async def profile_set_uid_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.message.text.strip()
    user_id = update.effective_user.id

    if not uid.isdigit() or len(uid) < 5:
        await update.message.reply_text("⚠️ UID обычно состоит из цифр. Проверь и введи снова.")
        return PROFILE_UID

    await set_bingx_uid(user_id, uid)
    await update.message.reply_text(
        f"✅ BingX UID сохранён: <code>{uid}</code>",
        parse_mode="HTML",
        reply_markup=back_main_keyboard(),
    )
    return ConversationHandler.END
