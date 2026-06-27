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

def generate_image(price: float, change_24h: float, direction: str,
                   rsi: float = 50, macd_lb: str = "—", fg_val: int = 50) -> bytes:
    W, H    = 900, 500
    BG      = (13, 13, 13)
    ORANGE  = (247, 147, 26)
    GREEN   = (39, 199, 112)
    RED     = (220, 60, 60)
    WHITE   = (255, 255, 255)
    GRAY    = (120, 130, 140)
    DARK2   = (26, 26, 26)
    DARK3   = (38, 38, 38)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

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

    f_huge  = load_font(FONT_PATHS, 80)
    f_large = load_font(FONT_PATHS, 44)
    f_med   = load_font(FONT_PATHS, 28)
    f_sm    = load_font(FONT_PATHS_REG, 22)
    f_xs    = load_font(FONT_PATHS_REG, 18)

    # ── Оранжевый хедер ──────────────────────────────────────────────
    HEADER_H = 60
    draw.rectangle([(0, 0), (W, HEADER_H)], fill=ORANGE)
    date_str = datetime.datetime.now().strftime("%d.%m.%Y · %H:%M МСК")
    draw.text((28, 14), "BTC ПРОГНОЗ", fill=(0, 0, 0), font=f_med)
    # дата справа
    date_w = draw.textlength(date_str, font=f_xs)
    draw.text((W - date_w - 24, 20), date_str, fill=(40, 20, 0), font=f_xs)

    # ── Цена + изменение (левая часть) ───────────────────────────────
    price_text = f"${price:,.0f}"
    draw.text((28, 80), price_text, fill=WHITE, font=f_huge)

    ch_color = GREEN if change_24h >= 0 else RED
    ch_sym   = "+" if change_24h >= 0 else ""
    draw.text((32, 172), f"{ch_sym}{change_24h:.2f}% за 24ч", fill=ch_color, font=f_sm)

    # ── Индикаторы (правая часть) ─────────────────────────────────────
    ind_x = 560
    draw.rectangle([(ind_x, 74), (W - 24, 210)], fill=DARK2)
    rsi_color = GREEN if rsi < 40 else RED if rsi > 65 else GRAY
    draw.text((ind_x + 16, 84),  f"RSI: {rsi:.0f}", fill=rsi_color, font=f_sm)
    draw.text((ind_x + 16, 118), f"MACD: {macd_lb}", fill=GRAY, font=f_xs)
    draw.text((ind_x + 16, 148), f"Fear & Greed: {fg_val}", fill=GRAY, font=f_xs)
    draw.text((ind_x + 16, 178), "@tokenruru", fill=(80, 80, 80), font=f_xs)

    # ── Блок прогноза ────────────────────────────────────────────────
    arrow_color = GREEN if direction == "UP" else RED
    pred_text   = "ВЫШЕ" if direction == "UP" else "НИЖЕ"
    arrow_sym   = "▲" if direction == "UP" else "▼"

    box_y1, box_y2 = 228, 360
    # Фон блока
    draw.rectangle([(24, box_y1), (W - 24, box_y2)], fill=DARK2)
    # Оранжевая рамка
    for t in range(3):
        draw.rectangle([(24 + t, box_y1 + t), (W - 24 - t, box_y2 - t)], outline=ORANGE)

    draw.text((50, box_y1 + 14), "ПРОГНОЗ НА 24Ч", fill=GRAY, font=f_xs)
    draw.text((50, box_y1 + 42), arrow_sym, fill=arrow_color, font=f_large)
    pred_x = 110
    draw.text((pred_x, box_y1 + 36), pred_text, fill=arrow_color, font=f_large)

    # ── Нижняя полоса (розыгрыш + бренд) ─────────────────────────────
    strip_y = 375
    draw.rectangle([(24, strip_y), (W - 24, H - 20)], fill=DARK2)
    draw.text((42, strip_y + 16), "7 дней подряд =", fill=GRAY, font=f_sm)
    usdt_x = 42 + int(draw.textlength("7 дней подряд = ", font=f_sm))
    draw.text((usdt_x, strip_y + 16), "100 USDT", fill=ORANGE, font=f_sm)

    bingx_w = int(draw.textlength("BingX", font=f_med))
    draw.text((W - bingx_w - 42, strip_y + 14), "BingX", fill=ORANGE, font=f_med)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
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
            "timestamp": datetime.datetime.utcnow().isoformat(),
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
        f"🗳 Согласен или нет? Напиши в обсуждении:\n"
        f"👍 <b>согласен</b> / 👎 <b>не согласен</b>\n"
        f"⏰ Голосование <b>1 час</b> · 🏆 7 дней подряд → <b>100 USDT</b>\n\n"
        f"Не финансовый совет.\n"
        f"Торгуй на BingX 👉 {REF_LINK}"
    )

    print("🖼 Генерирую картинку...")
    image_bytes = generate_image(price, market["change_24h"], direction,
                                 rsi=rsi, macd_lb=macd_lb, fg_val=fg["value"])

    send_photo(caption, image_bytes)
    save_cache(price, direction)
    print(f"💾 Кэш: {direction} от ${price:,.0f}")


if __name__ == "__main__":
    main()
