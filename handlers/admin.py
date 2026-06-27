from telegram import Update
from telegram.ext import ContextTypes
from database import set_vip, get_user
from config import ADMIN_IDS


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def grant_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ Нет доступа.")
        return

    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Использование: /grant_vip <user_id>")
        return

    target_id = int(args[0])
    user = await get_user(target_id)
    if not user:
        await update.message.reply_text(f"⚠️ Пользователь {target_id} не найден в базе.")
        return

    await set_vip(target_id, True)
    await update.message.reply_text(f"✅ VIP выдан пользователю {target_id}.")

    # Notify the user
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                "🎉 <b>Вам активирован VIP-доступ!</b>\n\n"
                "Теперь у вас:\n"
                "♾️ Безлимитные AI-запросы\n"
                "🤖 Улучшенная модель Claude Sonnet\n\n"
                "Приятной работы с TokenRu AI Terminal!"
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass


async def revoke_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ Нет доступа.")
        return

    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Использование: /revoke_vip <user_id>")
        return

    target_id = int(args[0])
    await set_vip(target_id, False)
    await update.message.reply_text(f"✅ VIP снят с пользователя {target_id}.")


async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "🛠 <b>Команды администратора</b>\n\n"
        "/grant_vip &lt;user_id&gt; — выдать VIP\n"
        "/revoke_vip &lt;user_id&gt; — снять VIP\n",
        parse_mode="HTML",
    )
