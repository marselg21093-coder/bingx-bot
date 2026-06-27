"""
BTC прогноз на 24 часа — @tokenruru
Динамическая картинка с ценой, стрелкой и BingX.
"""

import os
import sys
import io
import json
import datetime
import requests
import anthropic
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN  = os.environ["BOT_TOKEN"]
CLAUDE_KEY = os.environ["CLAUDE_API_KEY"]
CHANNEL_ID = "@tokenruru"
REF_LINK   = "https://bingx.com/ru/partner/A888"
CACHE_FILE = "cache/btc_prediction.json"


# ─── ГЕНЕРАЦИЯ КАРТИНКИ ───────────────────────────────────────────────────────

def generate_image(price: float, change_24h: float, direction: str) -> bytes:
    W, H = 900, 480

    BG      = (10, 20, 35)
    ORANGE  = (247, 147, 26)
    GREEN   = (39, 199, 112)
    RED     = (220, 60, 60)
    WHITE   = (255, 255, 255)
    GRAY    = (130, 145, 165)
    LINE    = (35, 55, 80)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Шрифты
    FONT_PATHS = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]
    FONT_PATHS_REG = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]

    def load_font(paths, size):
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
        return ImageFont.load_default()

    f_huge  = load_font(FONT_PATHS, 96)
    f_large = load_font(FONT_PATHS, 56)
    f_med   = load_font(FONT_PATHS, 36)
    f_sm    = load_font(FONT_PATHS_REG, 26)

    # Фон — тонкая текстура (градиент через полосы)
    for y in range(H):
        shade = int(10 + y * 8 / H)
        draw.line([(0, y), (W, y)], fill=(shade, shade + 10, shade + 22))

    # Левая оранжевая полоса
    draw.rectangle([(0, 0), (6, H)], fill=ORANGE)

    # BTC / USDT лейбл
    draw.text((40, 36), "BTC", fill=ORANGE, font=f_large)
    draw.text((155, 50), "/ USDT", fill=GRAY, font=f_med)

    # Цена
    price_text = f"${price:,.0f}"
    draw.text((40, 110), price_text, fill=WHITE, font=f_huge)

    # Изменение 24ч
    ch_color = GREEN if change_24h >= 0 else RED
    ch_text  = f"{change_24h:+.2f}% за 24ч"
    draw.text((44, 220), ch_text, fill=ch_color, font=f_med)

    # Разделитель
    draw.line([(40, 280), (W - 40, 280)], fill=LINE, width=2)

    # Прогноз
    arrow_color = GREEN if direction == "UP" else RED
    arrow_sym   = "▲" if direction == "UP" else "▼"
    pred_text   = "ПРОГНОЗ: ВЫШЕ" if direction == "UP" else "ПРОГНОЗ: НИЖЕ"

    draw.text((40, 300), arrow_sym, fill=arrow_color, font=f_huge)
    draw.text((150, 320), pred_text, fill=arrow_color, font=f_large)

    # Подпись прогноза
    draw.text((150, 385), "на следующие 24 часа", fill=GRAY, font=f_sm)

    # BingX брендинг — правый нижний угол
    draw.text((W - 190, H - 100), "BingX", fill=ORANGE, font=f_large)
    draw.text((W - 215, H - 48),  "@tokenruru", fill=GRAY, font=f_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()


# ─── ИНДИКАТОРЫ ───────────────────────────────────────────────────────────────

def get_market_data() -> dict:
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


def get_ohlc(days: int = 30) -> list:
    r = requests.get(
        "https://api.coingecko.com/api/v3/coins/bitcoin/ohlc",
        params={"vs_currency": "usd", "days": days},
        timeout=15,
    )
    return [{"c": x[4]} for x in r.json()]


def calc_rsi(closes: list, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    if al == 0:
        return 100.0
    return round(100 - 100 / (1 + ag / al), 1)


def calc_ema(values: list, period: int) -> list:
    ema = [values[0]]
    k = 2 / (period + 1)
    for v in values[1:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema


def calc_macd(closes: list) -> str:
    if len(closes) < 35:
        return "нет данных"
    ema12 = calc_ema(closes, 12)
    ema26 = calc_ema(closes, 26)
    macd  = [m - e for m, e in zip(ema12, ema26)]
    sig   = calc_ema(macd, 9)
    return "бычий ✅" if macd[-1] > sig[-1] else "медвежий ❌"


def calc_ma(closes: list, period: int):
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 0)


def get_fear_greed() -> dict:
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=2", timeout=8)
        data = r.json()["data"]
        return {
            "value": int(data[0]["value"]),
            "label": data[0]["value_classification"],
            "prev":  int(data[1]["value"]) if len(data) > 1 else int(data[0]["value"]),
        }
    except Exception:
        return {"value": 50, "label": "Neutral", "prev": 50}


def get_funding() -> str:
    try:
        r = requests.get(
            "https://fapi.binance.com/fapi/v1/fundingRate",
            params={"symbol": "BTCUSDT", "limit": 1},
            timeout=8,
        )
        f = float(r.json()[0]["fundingRate"]) * 100
        return f"{f:+.4f}%"
    except Exception:
        return "н/д"


def get_vol_avg(days: int = 7):
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
            params={"vs_currency": "usd", "days": days, "interval": "daily"},
            timeout=10,
        )
        vols = [v[1] for v in r.json()["total_volumes"]]
        return round(sum(vols) / len(vols), 0) if vols else None
    except Exception:
        return None


# ─── КЭШ ──────────────────────────────────────────────────────────────────────

def load_cache() -> dict:
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(price: float, direction: str) -> None:
    os.makedirs("cache", exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump({
            "date":      datetime.date.today().isoformat(),
            "price":     price,
            "direction": direction,
        }, f)


def yesterday_line(cache: dict, now_price: float) -> str:
    if not cache or not cache.get("price") or not cache.get("direction"):
        return ""
    prev_p = cache["price"]
    prev_d = cache["direction"]
    change = (now_price - prev_p) / prev_p * 100
    actual = "UP" if now_price > prev_p else "DOWN"
    ok = actual == prev_d
    arr = "⬆️" if actual == "UP" else "⬇️"
    return (
        f"{'✅' if ok else '❌'} Вчера: {'⬆️ ВЫШЕ' if prev_d == 'UP' else '⬇️ НИЖЕ'} "
        f"→ BTC {arr} {change:+.1f}% ({'Верно!' if ok else 'Неверно'})\n\n"
    )


# ─── AI-АНАЛИЗ ────────────────────────────────────────────────────────────────

SYSTEM = """
Ты технический аналитик BTC. Анализируй индикаторы и давай прогноз UP/DOWN на 24 часа.
Пиши 3-4 коротких предложения без лишних слов.
Без #, **, --, таблиц — только текст с эмодзи.
В конце обязательно напиши одну строку: ПРОГНОЗ: ВЫШЕ или ПРОГНОЗ: НИЖЕ
"""


def ask_claude(ind: str) -> tuple[str, str]:
    client = anthropic.Anthropic(api_key=CLAUDE_KEY)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=SYSTEM,
        messages=[{"role": "user", "content": ind}],
    )
    text = msg.content[0].text.strip()
    direction = "DOWN" if "ПРОГНОЗ: НИЖЕ" in text else "UP"
    analysis  = text.replace("ПРОГНОЗ: ВЫШЕ", "").replace("ПРОГНОЗ: НИЖЕ", "").strip()
    return analysis, direction


# ─── ОТПРАВКА ─────────────────────────────────────────────────────────────────

def send_photo(caption: str, image_bytes: bytes) -> None:
    if len(caption) > 1020:
        caption = caption[:1017] + "..."
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
        data={"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"},
        files={"photo": ("btc.png", image_bytes, "image/png")},
        timeout=30,
    )
    if r.json().get("ok"):
        print("✅ Пост отправлен")
    else:
        print(f"⚠️ Фото не прошло, отправляю текстом: {r.json().get('description')}")
        r2 = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHANNEL_ID, "text": caption,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=15,
        )
        if not r2.json().get("ok"):
            print(f"❌ Ошибка: {r2.json().get('description')}")
            sys.exit(1)


# ─── ГЛАВНАЯ ЛОГИКА ───────────────────────────────────────────────────────────

def main():
    print("📊 Получаю данные...")
    market  = get_market_data()
    price   = market["price"]
    ohlc    = get_ohlc(30)
    closes  = [c["c"] for c in ohlc]

    rsi     = calc_rsi(closes)
    macd_lb = calc_macd(closes)
    ma50    = calc_ma(closes, 50)
    fg      = get_fear_greed()
    funding = get_funding()
    vol_avg = get_vol_avg(7)

    rsi_lb  = "перепродан 🟢" if rsi < 30 else "перекуплен 🔴" if rsi > 70 else "нейтральный"
    ma50_d  = round((price / ma50 - 1) * 100, 1) if ma50 else None
    vol_pct = round(market["volume_24h"] / vol_avg * 100) if vol_avg else None
    fg_arr  = "↑" if fg["value"] > fg["prev"] else "↓" if fg["value"] < fg["prev"] else "→"

    ind_text = (
        f"BTC: ${price:,.0f} ({market['change_24h']:+.1f}% за 24ч, {market['change_7d']:+.1f}% за 7д)\n"
        f"Макс/мин 24ч: ${market['high_24h']:,.0f} / ${market['low_24h']:,.0f}\n"
        f"RSI(14): {rsi} — {rsi_lb}\n"
        f"MACD: {macd_lb}\n"
        + (f"MA50: ${ma50:,.0f} (цена {ma50_d:+.1f}%)\n" if ma50 else "")
        + f"Fear & Greed: {fg['value']} ({fg['label']}) {fg_arr}\n"
        + f"Фандинг: {funding}\n"
        + (f"Объём: {vol_pct}% от нормы" if vol_pct else "")
    )

    print("🤖 AI-анализ...")
    analysis, direction = ask_claude(ind_text)

    cache       = load_cache()
    yest_line   = yesterday_line(cache, price)
    dir_emoji   = "⬆️ ВЫШЕ" if direction == "UP" else "⬇️ НИЖЕ"
    date_str    = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    ma50_line   = f"MA50: ${ma50:,.0f} ({ma50_d:+.1f}%)\n" if ma50 else ""
    vol_line    = f"Объём: {vol_pct}% от нормы\n" if vol_pct else ""

    caption = (
        f"🔮 <b>BTC ПРОГНОЗ | {date_str} МСК</b>\n\n"
        f"{yest_line}"
        f"💰 <b>${price:,.0f}</b>  {market['change_24h']:+.1f}% за 24ч\n\n"
        f"📊 RSI: {rsi} ({rsi_lb})  |  MACD: {macd_lb}\n"
        f"{ma50_line}"
        f"😱 Страх/жадность: {fg['value']} ({fg['label']}) {fg_arr}\n"
        f"Фандинг: {funding}  {vol_line}\n"
        f"🤖 {analysis}\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>ПРОГНОЗ НА 24Ч: {dir_emoji}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"Не финансовый совет.\n"
        f"Торгуй на BingX 👉 {REF_LINK}"
    )

    print("🖼 Генерирую картинку...")
    image_bytes = generate_image(price, market["change_24h"], direction)

    send_photo(caption, image_bytes)
    save_cache(price, direction)
    print(f"💾 Кэш: {direction} от ${price:,.0f}")


if __name__ == "__main__":
    main()
