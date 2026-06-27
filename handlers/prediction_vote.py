"""
Система голосования за прогноз BTC.
Слушает группу @tokenru_online на "согласен" / "не согласен".
Результаты объявляет скрипт check_btc_prediction.py через Telegram.
"""

import os
import json
import datetime
import logging
import requests as req

from telegram import Update
from telegram.ext import ContextTypes

from database import save_vote, mark_votes_result, update_streak, get_giveaway_participants

logger = logging.getLogger(__name__)

# ID группы @tokenru_online — заполни после первого запуска (смотри в логах)
DISCUSSION_GROUP_ID = int(os.environ.get("DISCUSSION_GROUP_ID", "0"))
CHANNEL_ID          = "@tokenruru"
# URL сырого JSON-кэша предсказания (GitHub raw)
PREDICTION_CACHE_URL = os.environ.get(
    "PREDICTION_CACHE_URL",
    "https://raw.githubusercontent.com/ТВОЙ_ЛОГИН/ТВОЙ_РЕПО/main/cache/btc_prediction.json"
)
# Через сколько минут закрывается голосование
VOTE_WINDOW_MINUTES = 60

# Специальная команда от check_btc_prediction.py для обновления результатов
RESULT_PREFIX = "#PREDICTION_RESULT:"


def _get_today_prediction() -> dict | None:
    """Загружает сегодняшний прогноз из GitHub raw-файла."""
    try:
        r = req.get(PREDICTION_CACHE_URL, timeout=8)
        data = r.json()
        if data.get("date") != datetime.date.today().isoformat():
            return None  # Прогноз не на сегодня
        return data
    except Exception as e:
        logger.warning(f"Не могу загрузить прогноз: {e}")
        return None


def _is_vote_window_open(prediction: dict) -> bool:
    """Проверяет, открыто ли окно голосования (60 минут)."""
    ts = prediction.get("timestamp")
    if not ts:
        return False
    try:
        posted_at = datetime.datetime.fromisoformat(ts)
        now = datetime.datetime.now()
        diff = (now - posted_at).total_seconds() / 60
        return 0 <= diff <= VOTE_WINDOW_MINUTES
    except Exception:
        return False


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главный хендлер сообщений в группе tokenru_online."""
    msg  = update.message
    if not msg or not msg.text:
        return

    chat_id = msg.chat_id

    # Логируем ID группы при первом запуске (чтобы заполнить DISCUSSION_GROUP_ID)
    if DISCUSSION_GROUP_ID == 0:
        logger.info(f"Сообщение из чата ID: {chat_id}  —  заполни DISCUSSION_GROUP_ID={chat_id}")
        return

    if chat_id != DISCUSSION_GROUP_ID:
        return

    text = msg.text.strip()

    # ── Обработка служебной команды от check_btc_prediction.py ──────────────
    if text.startswith(RESULT_PREFIX):
        await _process_result_command(text, context)
        return

    # ── Обработка голоса ──────────────────────────────────────────────────────
    lower = text.lower()
    if "согласен" in lower:
        vote = "agree"
    elif "не согласен" in lower:
        vote = "disagree"
    else:
        return

    prediction = _get_today_prediction()
    if not prediction:
        return

    if not _is_vote_window_open(prediction):
        return

    user     = msg.from_user
    user_id  = user.id
    username = user.username or ""
    fname    = user.first_name or ""
    date     = prediction["date"]

    saved = await save_vote(date, user_id, username, fname, vote)
    if not saved:
        # Уже голосовал — тихо игнорируем
        return

    direction = prediction.get("direction", "UP")
    pred_text = "⬆️ ВЫШЕ" if direction == "UP" else "⬇️ НИЖЕ"
    agree_text = "✅ Согласен" if vote == "agree" else "❌ Не согласен"

    name_display = f"@{username}" if username else fname
    await msg.reply_text(
        f"{agree_text}, {name_display}!\n\n"
        f"Прогноз на сегодня: {pred_text}\n"
        f"Узнаем результат завтра в 14:50 МСК 🔔\n\n"
        f"Угадай 7 дней подряд → участвуй в розыгрыше 100 USDT 🎁"
    )
    logger.info(f"Голос сохранён: {user_id} ({username}) → {vote} за {date}")


async def _process_result_command(text: str, context) -> None:
    """
    Обрабатывает команду от check_btc_prediction.py.
    Формат: #PREDICTION_RESULT:DATE:CORRECT_VOTE:PREV_PRICE:CURR_PRICE
    Пример: #PREDICTION_RESULT:2026-06-27:agree:60514:61200
    """
    try:
        parts        = text.replace(RESULT_PREFIX, "").split(":")
        date         = parts[0]   # 2026-06-27
        correct_vote = parts[1]   # agree / disagree
        prev_price   = float(parts[2])
        curr_price   = float(parts[3])
    except Exception as e:
        logger.error(f"Ошибка парсинга результата: {e}")
        return

    winners = await mark_votes_result(date, correct_vote)
    direction_text = "⬆️ ВЫШЕ" if correct_vote == "agree" else "⬇️ НИЖЕ"
    change = (curr_price - prev_price) / prev_price * 100
    actual_arrow = "⬆️" if curr_price > prev_price else "⬇️"

    # Обновляем серии победителей
    new_qualifiers = []
    for w in winners:
        streak_data = await update_streak(
            w["user_id"], w["username"], w["first_name"],
            correct=True, date=date
        )
        if streak_data["current_streak"] >= 7 and streak_data["giveaway_round"] == 1:
            new_qualifiers.append((w, streak_data))

    # Обновляем серии проигравших (у них streak сбрасывается)
    from database import get_votes_for_date
    all_votes = await get_votes_for_date(date)
    losers = [v for v in all_votes if v["vote"] != correct_vote]
    for l in losers:
        await update_streak(l["user_id"], l["username"], l["first_name"], correct=False, date=date)

    total_votes   = len(all_votes)
    correct_count = len(winners)

    # Формируем сообщение с результатами
    lines = [
        f"📊 <b>Итоги прогноза за {date}</b>\n",
        f"Вчера: {direction_text}",
        f"BTC: ${prev_price:,.0f} → ${curr_price:,.0f} {actual_arrow} {change:+.1f}%\n",
        f"{'✅ Прогноз верный!' if correct_count > 0 else '❌ Прогноз не угадали'}\n",
        f"👥 Проголосовало: {total_votes}",
        f"🎯 Угадали: {correct_count} из {total_votes}",
    ]

    if new_qualifiers:
        lines.append("\n🏆 <b>Попали в розыгрыш 100 USDT:</b>")
        for (w, s) in new_qualifiers:
            name = f"@{w['username']}" if w["username"] else w["first_name"]
            lines.append(f"🎉 {name} — серия {s['current_streak']} дней!")

    # Список текущих участников розыгрыша
    participants = await get_giveaway_participants()
    if participants:
        lines.append(f"\n🎁 <b>Участники розыгрыша ({len(participants)} чел.):</b>")
        for p in participants[:10]:
            name = f"@{p['username']}" if p["username"] else p["first_name"]
            lines.append(f"• {name} — серия {p['current_streak']} дней")
        if len(participants) > 10:
            lines.append(f"  ...и ещё {len(participants) - 10} участников")

    lines.append("\n⏰ Новый прогноз выйдет сегодня в 15:00 МСК")
    lines.append("Угадай 7 дней подряд → 100 USDT 🎁")

    result_text = "\n".join(lines)

    # Публикуем в группе и в канале
    bot = context.bot
    await bot.send_message(
        chat_id=DISCUSSION_GROUP_ID,
        text=result_text,
        parse_mode="HTML",
    )
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=result_text,
        parse_mode="HTML",
    )
    logger.info(f"Результаты опубликованы: {correct_count}/{total_votes} верных за {date}")


async def cmd_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /розыгрыш — показывает текущих участников."""
    participants = await get_giveaway_participants()
    if not participants:
        await update.message.reply_text("Пока нет участников. Угадай 7 дней подряд! 🎯")
        return

    lines = [f"🎁 <b>Участники розыгрыша 100 USDT</b> ({len(participants)} чел.)\n"]
    for i, p in enumerate(participants, 1):
        name = f"@{p['username']}" if p["username"] else p["first_name"]
        lines.append(f"{i}. {name} — серия {p['current_streak']} дней 🔥")
    lines.append("\nУгадай 7 дней подряд — попадёшь в список!")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
