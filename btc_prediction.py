"""
BTC прогноз на 24 часа — @tokenruru
Анализирует реальные индикаторы и делает прогноз UP/DOWN.
Вчерашний прогноз хранится в файле cache/btc_prediction.json (git commit).
"""

import os
import sys
import json
import datetime
import requests
import anthropic

BOT_TOKEN  = os.environ["BOT_TOKEN"]
CLAUDE_KEY = os.environ["CLAUDE_API_KEY"]
CHANNEL_ID = "@tokenruru"
REF_LINK   = "https://bingx.com/ru/partner/A888"
CACHE_FILE = "cache/btc_prediction.json"

IMAGES = [
    "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=900&q=80",
    "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=900&q=80",
    "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=900&q=80",
    "https://images.unsplash.com/photo-1640340434855-6084b1f4901c?w=900&q=80",
    "https://images.unsplash.com/photo-1622630998477-20aa696ecb05?w=900&q=80",
    "https://images.unsplash.com/photo-1605792657660-596af9009e82?w=900&q=80",
]


# ─── ИНДИКАТОРЫ ───────────────────────────────────────────────────────────────

def get_ohlc(days: int = 30) -> list[dict]:
    """OHLC данные BTC с CoinGecko (дневные свечи)."""
    r = requests.get(
        "https://api.coingecko.com/api/v3/coins/bitcoin/ohlc",
        params={"vs_currency": "usd", "days": days},
        timeout=15,
    )
    raw = r.json()
    return [{"ts": x[0], "o": x[1], "h": x[2], "l": x[3], "c": x[4]} for x in raw]


def get_market_data() -> dict:
    """Цена, объём, изменения с CoinGecko."""
    r = requests.get(
        "https://api.coingecko.com/api/v3/coins/bitcoin",
        params={"localization": "false", "tickers": "false",
                "market_data": "true", "community_data": "false"},
        timeout=10,
    )
    d = r.json()["market_data"]
    return {
        "price":      d["current_price"]["usd"],
        "change_24h": d["price_change_percentage_24h"] or 0,
        "change_7d":  d["price_change_percentage_7d"] or 0,
        "volume_24h": d["total_volume"]["usd"],
        "high_24h":   d["high_24h"]["usd"],
        "low_24h":    d["low_24h"]["usd"],
    }


def calc_rsi(closes: list[float], period: int = 14) -> float:
    """RSI классический (Wilder)."""
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def calc_ema(values: list[float], period: int) -> list[float]:
    ema = [values[0]]
    k = 2 / (period + 1)
    for v in values[1:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema


def calc_macd(closes: list[float]) -> tuple[float, float, str]:
    """MACD (12, 26, 9). Возвращает (macd_line, signal, сигнал)."""
    if len(closes) < 35:
        return 0, 0, "нет данных"
    ema12 = calc_ema(closes, 12)
    ema26 = calc_ema(closes, 26)
    macd_line = [m - e for m, e in zip(ema12, ema26)]
    signal    = calc_ema(macd_line, 9)
    m = macd_line[-1]
    s = signal[-1]
    label = "бычий пересёк вверх" if m > s else "медвежий пересёк вниз"
    return round(m, 1), round(s, 1), label


def calc_ma(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 0)


def get_fear_greed() -> dict:
    """Fear & Greed Index с alternative.me."""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=2", timeout=8)
        data = r.json()["data"]
        today = data[0]
        yest  = data[1] if len(data) > 1 else data[0]
        return {
            "value":       int(today["value"]),
            "label":       today["value_classification"],
            "prev_value":  int(yest["value"]),
        }
    except Exception:
        return {"value": 50, "label": "Neutral", "prev_value": 50}


def get_funding_rate() -> float | None:
    """Funding Rate BTCUSDT с Binance фьючерсов (публичный API)."""
    try:
        r = requests.get(
            "https://fapi.binance.com/fapi/v1/fundingRate",
            params={"symbol": "BTCUSDT", "limit": 1},
            timeout=8,
        )
        data = r.json()
        return round(float(data[0]["fundingRate"]) * 100, 4)  # в %
    except Exception:
        return None


def get_volume_avg(days: int = 7) -> float | None:
    """Средний объём BTC за N дней (CoinGecko market chart)."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
            params={"vs_currency": "usd", "days": days, "interval": "daily"},
            timeout=10,
        )
        volumes = [v[1] for v in r.json()["total_volumes"]]
        return round(sum(volumes) / len(volumes), 0) if volumes else None
    except Exception:
        return None


# ─── КЭШ (вчерашний прогноз) ──────────────────────────────────────────────────

def load_cache() -> dict:
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(data: dict) -> None:
    os.makedirs("cache", exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)


def yesterday_result(cache: dict, current_price: float) -> str:
    """Строка о вчерашнем прогнозе — угадали или нет."""
    if not cache:
        return ""
    prev_price     = cache.get("price")
    prev_direction = cache.get("direction")  # "UP" или "DOWN"
    prev_date      = cache.get("date")
    if not all([prev_price, prev_direction, prev_date]):
        return ""

    change = (current_price - prev_price) / prev_price * 100
    actual = "UP" if current_price > prev_price else "DOWN"
    correct = actual == prev_direction

    emoji_result = "✅" if correct else "❌"
    arrow = "⬆️" if actual == "UP" else "⬇️"
    return (
        f"{emoji_result} <b>Вчерашний прогноз:</b> {'⬆️ ВЫШЕ' if prev_direction == 'UP' else '⬇️ НИЖЕ'}\n"
        f"📍 Результат: BTC {arrow} {change:+.1f}% → {'Угадали!' if correct else 'Не угадали'}\n\n"
    )


# ─── AI-АНАЛИЗ ────────────────────────────────────────────────────────────────

SYSTEM = """
Ты старший технический аналитик крипторынка. Анализируешь BTC на следующие 24 часа.
Твоя задача — на основе реальных индикаторов дать конкретный прогноз: ВЫШЕ или НИЖЕ.

Правила:
- Пиши коротко и по делу, 4-5 предложений
- Назови 2-3 главных аргумента для твоего прогноза
- Будь честным — если сигналы смешанные, скажи это
- Только эмодзи как разделители, без #, **, --, таблиц
- Заканчивай строкой: Не финансовый совет — только образовательный анализ.
"""


def ask_claude(indicators_text: str) -> tuple[str, str]:
    """Возвращает (анализ, направление UP/DOWN)."""
    client = anthropic.Anthropic(api_key=CLAUDE_KEY)

    prompt = (
        f"{indicators_text}\n\n"
        "На основе этих данных:\n"
        "1. Дай краткий анализ (4-5 предложений)\n"
        "2. В самом конце напиши одну строку ровно в таком формате:\n"
        "ПРОГНОЗ: ВЫШЕ или ПРОГНОЗ: НИЖЕ"
    )

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()

    direction = "UP"
    if "ПРОГНОЗ: НИЖЕ" in text:
        direction = "DOWN"
    elif "ПРОГНОЗ: ВЫШЕ" in text:
        direction = "UP"

    # Убираем строку с прогнозом из видимого анализа
    analysis = text.replace("ПРОГНОЗ: ВЫШЕ", "").replace("ПРОГНОЗ: НИЖЕ", "").strip()
    return analysis, direction


# ─── ОТПРАВКА ─────────────────────────────────────────────────────────────────

def send_photo(caption: str) -> None:
    day = datetime.date.today().timetuple().tm_yday
    image_url = IMAGES[day % len(IMAGES)]
    if len(caption) > 1020:
        caption = caption[:1017] + "..."
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
        json={"chat_id": CHANNEL_ID, "photo": image_url,
              "caption": caption, "parse_mode": "HTML"},
        timeout=15,
    )
    if r.json().get("ok"):
        print("✅ Прогноз отправлен")
    else:
        print(f"⚠️ Фото не прошло, отправляю текстом: {r.json().get('description')}")
        r2 = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHANNEL_ID, "text": caption,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10,
        )
        if not r2.json().get("ok"):
            print(f"❌ Ошибка: {r2.json().get('description')}")
            sys.exit(1)


# ─── ГЛАВНАЯ ЛОГИКА ───────────────────────────────────────────────────────────

def main():
    print("📊 Получаю данные...")

    # Рыночные данные
    market   = get_market_data()
    price    = market["price"]
    ohlc     = get_ohlc(30)
    closes   = [c["c"] for c in ohlc]

    # Индикаторы
    rsi      = calc_rsi(closes)
    macd_v, signal_v, macd_label = calc_macd(closes)
    ma50     = calc_ma(closes, 50)
    ma200    = calc_ma(closes, 200)
    fg       = get_fear_greed()
    funding  = get_funding_rate()
    vol_avg  = get_volume_avg(7)

    # RSI интерпретация
    rsi_label = "перепродан" if rsi < 30 else "перекуплен" if rsi > 70 else "нейтральный"

    # MA интерпретация
    ma50_diff = round((price / ma50 - 1) * 100, 1) if ma50 else None
    ma200_diff = round((price / ma200 - 1) * 100, 1) if ma200 else None

    # Объём vs среднее
    vol_ratio = round(market["volume_24h"] / vol_avg * 100, 0) if vol_avg else None

    # Fear & Greed изменение
    fg_change = fg["value"] - fg["prev_value"]
    fg_arrow = "↑" if fg_change > 0 else "↓" if fg_change < 0 else "→"

    # Funding label
    if funding is not None:
        if funding > 0.05:
            fund_label = "высокий — лонги перегреты"
        elif funding < -0.01:
            fund_label = "отрицательный — шортисты доминируют"
        else:
            fund_label = "нейтральный"
    else:
        fund_label = "нет данных"

    # Строка для Claude
    indicators_text = (
        f"BTC/USDT сейчас: ${price:,.0f}\n"
        f"Изменение 24ч: {market['change_24h']:+.1f}%\n"
        f"Изменение 7д: {market['change_7d']:+.1f}%\n"
        f"Максимум 24ч: ${market['high_24h']:,.0f}\n"
        f"Минимум 24ч: ${market['low_24h']:,.0f}\n"
        f"RSI(14): {rsi} — {rsi_label}\n"
        f"MACD: {macd_label} (MACD={macd_v}, Signal={signal_v})\n"
        f"MA50: ${ma50:,.0f} (цена {ma50_diff:+.1f}% от MA50)\n" if ma50 else ""
        f"MA200: ${ma200:,.0f} (цена {ma200_diff:+.1f}% от MA200)\n" if ma200 else ""
        f"Fear & Greed: {fg['value']} ({fg['label']}) {fg_arrow} с {fg['prev_value']} вчера\n"
        f"Объём 24ч: ${market['volume_24h']/1e9:.1f}B"
        + (f" ({vol_ratio:.0f}% от среднего за 7д)" if vol_ratio else "") + "\n"
        + (f"Funding Rate: {funding:+.4f}% — {fund_label}\n" if funding is not None else "")
    )

    print("🤖 Запрашиваю AI-анализ...")
    analysis, direction = ask_claude(indicators_text)

    # Вчерашний прогноз
    cache = load_cache()
    result_line = yesterday_result(cache, price)

    # Прогноз стрелка
    dir_emoji = "⬆️ ВЫШЕ" if direction == "UP" else "⬇️ НИЖЕ"
    date_str  = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    # Индикаторы для поста
    ma_lines = ""
    if ma50:
        ma_lines += f"MA50: ${ma50:,.0f} ({ma50_diff:+.1f}%)\n"
    if ma200:
        ma_lines += f"MA200: ${ma200:,.0f} ({ma200_diff:+.1f}%)\n"

    fund_line = f"Фандинг: {funding:+.4f}% — {fund_label}\n" if funding is not None else ""
    vol_line  = f"Объём: {vol_ratio:.0f}% от нормы" if vol_ratio else "Объём: нет данных"

    caption = (
        f"🔮 <b>BTC ПРОГНОЗ НА 24 ЧАСА | {date_str} МСК</b>\n\n"
        f"{result_line}"
        f"💰 Сейчас: <b>${price:,.0f}</b> ({market['change_24h']:+.1f}% за 24ч)\n\n"
        f"📊 <b>Индикаторы:</b>\n"
        f"RSI(14): {rsi} — {rsi_label}\n"
        f"MACD: {macd_label}\n"
        f"{ma_lines}"
        f"😱 Страх и жадность: {fg['value']} ({fg['label']}) {fg_arrow}\n"
        f"{fund_line}"
        f"{vol_line}\n\n"
        f"🤖 <b>ИИ-анализ:</b>\n"
        f"{analysis}\n\n"
        f"🎯 <b>Прогноз на 24ч: {dir_emoji}</b>\n\n"
        f"Не финансовый совет — только образовательный анализ.\n"
        f"Торгуй на BingX 👉 {REF_LINK}"
    )

    send_photo(caption)

    # Сохраняем сегодняшний прогноз для завтра
    save_cache({
        "date":      datetime.date.today().isoformat(),
        "price":     price,
        "direction": direction,
    })
    print(f"💾 Кэш сохранён: {direction} от ${price:,.0f}")


if __name__ == "__main__":
    main()
