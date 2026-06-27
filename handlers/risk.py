from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from handlers.common import cancel
from handlers.keyboards import back_main_keyboard

DEPOSIT, RISK_PCT, ENTRY, STOP, DIRECTION = range(5)


async def risk_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.message.reply_text(
        "⚖️ <b>Риск-менеджер</b>\n\n"
        "Шаг 1/5: Введи размер депозита в $\n"
        "Пример: <code>1000</code>\n\n"
        "Или /cancel для отмены.",
        parse_mode="HTML",
    )
    return DEPOSIT


async def risk_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = float(update.message.text.strip().replace(",", "."))
        if val <= 0:
            raise ValueError
        context.user_data["deposit"] = val
        await update.message.reply_text(
            "Шаг 2/5: Риск на сделку в %\n"
            "Рекомендация: 1-2%\n"
            "Пример: <code>2</code>",
            parse_mode="HTML",
        )
        return RISK_PCT
    except ValueError:
        await update.message.reply_text("⚠️ Введи число, например: 1000")
        return DEPOSIT


async def risk_pct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = float(update.message.text.strip().replace(",", "."))
        if val <= 0 or val > 100:
            raise ValueError
        context.user_data["risk_pct"] = val
        await update.message.reply_text(
            "Шаг 3/5: Цена входа в $\n"
            "Пример: <code>60000</code>",
            parse_mode="HTML",
        )
        return ENTRY
    except ValueError:
        await update.message.reply_text("⚠️ Введи число от 0.01 до 100")
        return RISK_PCT


async def risk_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = float(update.message.text.strip().replace(",", "."))
        if val <= 0:
            raise ValueError
        context.user_data["entry"] = val
        await update.message.reply_text(
            "Шаг 4/5: Цена стоп-лосса в $\n"
            "Пример: <code>58000</code>",
            parse_mode="HTML",
        )
        return STOP
    except ValueError:
        await update.message.reply_text("⚠️ Введи корректную цену, например: 60000")
        return ENTRY


async def risk_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        val = float(update.message.text.strip().replace(",", "."))
        if val <= 0:
            raise ValueError
        context.user_data["stop"] = val
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📈 Лонг", callback_data="risk_dir_long"),
                InlineKeyboardButton("📉 Шорт", callback_data="risk_dir_short"),
            ]
        ])
        await update.message.reply_text("Шаг 5/5: Направление сделки", reply_markup=kb)
        return DIRECTION
    except ValueError:
        await update.message.reply_text("⚠️ Введи корректную цену стоп-лосса")
        return STOP


async def risk_direction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    direction = "long" if query.data == "risk_dir_long" else "short"

    d = context.user_data
    deposit   = d["deposit"]
    risk_pct  = d["risk_pct"]
    entry     = d["entry"]
    stop      = d["stop"]

    risk_usd = deposit * (risk_pct / 100)

    if direction == "long":
        sl_distance = entry - stop
        dir_emoji = "📈 Лонг"
    else:
        sl_distance = stop - entry
        dir_emoji = "📉 Шорт"

    if sl_distance <= 0:
        await query.message.reply_text(
            "⚠️ Стоп-лосс должен быть ниже цены входа для лонга (выше для шорта). Начни заново.",
            reply_markup=back_main_keyboard(),
        )
        context.user_data.clear()
        return ConversationHandler.END

    sl_pct     = (sl_distance / entry) * 100
    pos_usd    = risk_usd / sl_pct * 100
    pos_units  = pos_usd / entry
    leverage   = pos_usd / deposit

    # Оценка риска
    if risk_pct <= 1:
        risk_label = "🟢 Низкий"
    elif risk_pct <= 2:
        risk_label = "🟡 Умеренный"
    elif risk_pct <= 5:
        risk_label = "🟠 Высокий"
    else:
        risk_label = "🔴 Очень высокий"

    result = (
        f"⚖️ <b>Результат расчёта</b>\n\n"
        f"Направление: {dir_emoji}\n"
        f"Депозит: <b>${deposit:,.2f}</b>\n"
        f"Риск: <b>{risk_pct}%</b> = <b>${risk_usd:,.2f}</b>\n\n"
        f"📍 Цена входа: <b>${entry:,.2f}</b>\n"
        f"🛑 Стоп-лосс: <b>${stop:,.2f}</b>\n"
        f"📏 Расстояние до стопа: <b>{sl_pct:.2f}%</b>\n\n"
        f"💼 <b>Размер позиции:</b>\n"
        f"• В USD: <b>${pos_usd:,.2f}</b>\n"
        f"• В монетах: <b>{pos_units:.6f}</b>\n"
        f"• Плечо: <b>~{leverage:.1f}x</b>\n\n"
        f"🎯 Оценка риска: {risk_label}\n\n"
    )

    if risk_pct > 2:
        result += "⚠️ <i>Рекомендуем снизить риск до 1-2% на сделку.</i>\n"
    if leverage > 10:
        result += "⚠️ <i>Плечо выше 10x — очень высокий риск ликвидации.</i>\n"

    result += "\n⚠️ <i>Это не финансовая рекомендация. Используйте риск-менеджмент.</i>"

    context.user_data.clear()
    await query.message.reply_text(result, parse_mode="HTML", reply_markup=back_main_keyboard())
    return ConversationHandler.END
