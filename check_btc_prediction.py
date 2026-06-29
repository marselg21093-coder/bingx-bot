"""
Проверка результата BTC прогноза.
Запускается в 14:50 МСК — до нового прогноза в 15:00.
Сравнивает вчерашний прогноз с текущей ценой BTC.
Отправляет результат боту через сообщение в группу.
"""

import os
import sys
import datetime
import requests

BOT_TOKEN            = os.environ["BOT_TOKEN"]
DISCUSSION_GROUP_ID  = os.environ.get("DISCUSSION_GROUP_ID", "-1001953059519")
PREDICTION_CACHE_URL = os.environ.get(
    "PREDICTION_CACHE_URL",
    "https://raw.githubusercontent.com/marselg21093-coder/bingx-bot/main/cache/btc_prediction.json"
)


def get_cached_prediction() -> dict | None:
    """Загружает кэш прогноза с GitHub."""
    try:
        r = requests.get(PREDICTION_CACHE_URL, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Ошибка загрузки кэша: {e}")
        return None


def get_btc_price() -> float | None:
    """Получает текущую цену BTC с CoinGecko."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=10,
        )
        return float(r.json()["bitcoin"]["usd"])
    except Exception as e:
        print(f"Ошибка CoinGecko: {e}")
        return None


def send_message(text: str) -> None:
    """Отправляет сообщение в группу."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(
        url,
        json={"chat_id": DISCUSSION_GROUP_ID, "text": text},
        timeout=15,
    )
    if r.json().get("ok"):
        print("✅ Сообщение отправлено боту")
    else:
        print(f"❌ Ошибка Telegram: {r.json().get('description')}")
        sys.exit(1)


def main():
    prediction = get_cached_prediction()
    if not prediction:
        print("❌ Нет кэша прогноза — пропускаем")
        sys.exit(1)

    date       = prediction["date"]
    prev_price = float(prediction["price"])
    direction  = prediction["direction"]  # UP или DOWN

    # Проверяем что это вчерашний прогноз
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    if date != yesterday:
        print(f"⚠️ Кэш за {date}, ожидали {yesterday} — продолжаем всё равно")

    curr_price = get_btc_price()
    if not curr_price:
        print("❌ Не удалось получить цену BTC")
        sys.exit(1)

    # Определяем верный голос
    if direction == "UP":
        correct_vote = "agree" if curr_price > prev_price else "disagree"
    else:  # DOWN
        correct_vote = "agree" if curr_price < prev_price else "disagree"

    print(f"Прогноз: {direction} | Вчера: ${prev_price:,.0f} | Сейчас: ${curr_price:,.0f}")
    print(f"Верный голос: {correct_vote}")

    # Отправляем команду боту в группу
    message = f"#PREDICTION_RESULT:{date}:{correct_vote}:{prev_price:.0f}:{curr_price:.0f}"
    send_message(message)


if __name__ == "__main__":
    main()
