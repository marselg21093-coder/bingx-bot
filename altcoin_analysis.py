"""
Ежедневный разбор альткоинов для @tokenruru
Выходит каждый день в 19:00 МСК
ETH всегда + ротация монеты по дням недели
"""

import os
import sys
import random
import requests
import datetime
import anthropic

BOT_TOKEN  = os.environ["BOT_TOKEN"]
CLAUDE_KEY = os.environ["CLAUDE_API_KEY"]
CHANNEL_ID = "@tokenruru"
REF_LINK   = "https://bingx.com/ru/partner/A888"

# ─── РОТАЦИЯ МОНЕТ ────────────────────────────────────────────────────────────
# Ключ: день недели (0=пн, 6=вс). Значение: (тикер, CoinGecko ID, описание)
ROTATION = {
    0: ("SOL",   "solana",        "Solana — быстрый L1"),
    1: ("ARB",   "arbitrum",      "Arbitrum — лидер L2"),
    2: ("AVAX",  "avalanche-2",   "Avalanche — мультичейн"),
    3: ("BNB",   "binancecoin",   "BNB — монета Binance"),
    4: ("DOT",   "polkadot",      "Polkadot — мультичейн"),
    5: ("POL",   "polygon-ecosystem-token", "Polygon/POL — Ethereum L2"),
    6: None,  # Воскресенье — итог недели
}

IMAGES = [
    "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=900&q=80",
    "https://images.unsplash.com/photo-1640340434855-6084b1f4901c?w=900&q=80",
    "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=900&q=80",
    "https://images.unsplash.com/photo-1622630998477-20aa696ecb05?w=900&q=80",
    "https://images.unsplash.com/photo-1605792657660-596af9009e82?w=900&q=80",
    "https://images.unsplash.com/photo-1609554496796-c345a5335ceb?w=900&q=80",
]

SYSTEM_PROMPT = """
Ты аналитик крипторынка для Telegram-канала русскоязычных трейдеров.
Пиши кратко и по делу — максимум 5-6 строк на монету.
Правила форматирования — строго обязательны:
- Только эмодзи как разделители, без # ## ** -- и таблиц
- Никаких заголовков с решётками и звёздочками
- Никаких горизонтальных линий из символов
- Простой текст с эмодзи

Структура каждого разбора:
📈 или 📉 Тренд — одно предложение что происходит
🎯 Поддержка X — Сопротивление X
👀 На что смотреть сегодня — одно предложение
⚠️ Главный риск — одно предложение

Это образовательный анализ. Заканчивай строкой:
Не торговый сигнал — делай собственный анализ.
"""

SYSTEM_WEEKLY = """
Ты аналитик крипторынка для Telegram-канала русскоязычных трейдеров.
Пишешь воскресный итог недели — кратко, 6-8 строк.
Правила форматирования — строго обязательны:
- Только эмодзи как разделители, без # ## ** и таблиц
- Никаких заголовков, никаких горизонтальных линий
- Простой текст с эмодзи

Структура:
📊 Настроение рынка за неделю — одно предложение
🚀 Лидеры роста — кратко
📉 Аутсайдеры — кратко
👀 На что смотреть на следующей неделе
💡 Главный вывод для трейдера

Заканчивай: Не торговый сигнал — делай собственный анализ.
"""


# ─── ДАННЫЕ ──────────────────────────────────────────────────────────────────

def fetch_coin_data(coin_id: str) -> dict | None:
    """Получить данные монеты с CoinGecko."""
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}",
            params={"localization": "false", "tickers": "false",
                    "market_data": "true", "community_data": "false",
                    "developer_data": "false"},
            timeout=10,
        )
        d = r.json()
        md = d["market_data"]
        return {
            "name":       d["name"],
            "symbol":     d["symbol"].upper(),
            "price":      md["current_price"]["usd"],
            "change_24h": md["price_change_percentage_24h"] or 0,
            "change_7d":  md["price_change_percentage_7d"] or 0,
            "high_24h":   md["high_24h"]["usd"],
            "low_24h":    md["low_24h"]["usd"],
            "volume_24h": md["total_volume"]["usd"],
            "market_cap": md["market_cap"]["usd"],
        }
    except Exception as e:
        print(f"Ошибка CoinGecko для {coin_id}: {e}")
        return None


def fetch_weekly_top() -> str:
    """Топ-5 роста и падения за неделю с CoinGecko."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 50,
                "page": 1,
                "price_change_percentage": "7d",
            },
            timeout=10,
        )
        coins = r.json()
        sorted_coins = sorted(
            coins,
            key=lambda x: x.get("price_change_percentage_7d_in_currency") or 0,
            reverse=True,
        )
        top5 = sorted_coins[:5]
        bot5 = sorted_coins[-5:]

        top_str = ", ".join(
            f"{c['symbol'].upper()} ({c.get('price_change_percentage_7d_in_currency', 0):+.1f}%)"
            for c in top5
        )
        bot_str = ", ".join(
            f"{c['symbol'].upper()} ({c.get('price_change_percentage_7d_in_currency', 0):+.1f}%)"
            for c in bot5
        )
        return f"Топ роста за неделю: {top_str}\nТоп падения за неделю: {bot_str}"
    except Exception as e:
        print(f"Ошибка недельной статистики: {e}")
        return "Данные за неделю временно недоступны"


def format_coin_prompt(data: dict, description: str) -> str:
    vol = data["volume_24h"]
    vol_str = f"${vol/1e9:.1f}B" if vol >= 1e9 else f"${vol/1e6:.0f}M"
    return (
        f"Монета: {data['name']} ({data['symbol']}) — {description}\n"
        f"Цена: ${data['price']:,.4f}\n"
        f"Изменение 24ч: {data['change_24h']:+.2f}%\n"
        f"Изменение 7д:  {data['change_7d']:+.2f}%\n"
        f"Максимум 24ч:  ${data['high_24h']:,.4f}\n"
        f"Минимум 24ч:   ${data['low_24h']:,.4f}\n"
        f"Объём 24ч:     {vol_str}\n"
        f"Сделай образовательный разбор для трейдеров."
    )


# ─── AI-АНАЛИЗ ────────────────────────────────────────────────────────────────

def ask_claude(system: str, prompt: str) -> str:
    client = anthropic.Anthropic(api_key=CLAUDE_KEY)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


# ─── ОТПРАВКА ─────────────────────────────────────────────────────────────────

def send_photo(caption: str) -> None:
    """Отправить пост с картинкой. При ошибке — текстом."""
    image_url = random.choice(IMAGES)
    # Telegram caption limit = 1024 chars
    if len(caption) > 1020:
        caption = caption[:1017] + "..."

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    resp = requests.post(
        url,
        json={"chat_id": CHANNEL_ID, "photo": image_url,
              "caption": caption, "parse_mode": "HTML"},
        timeout=15,
    )
    result = resp.json()
    if result.get("ok"):
        print("✅ Разбор с картинкой отправлен")
    else:
        print(f"⚠️ Картинка не загрузилась, отправляю текстом: {result.get('description')}")
        url2 = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp2 = requests.post(
            url2,
            json={"chat_id": CHANNEL_ID, "text": caption,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=15,
        )
        if not resp2.json().get("ok"):
            print(f"❌ Ошибка Telegram: {resp2.json().get('description')}")
            sys.exit(1)


# ─── ЗАГОЛОВОК ПОСТА ──────────────────────────────────────────────────────────

def day_header(weekday: int, ticker: str | None) -> str:
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    date_str = datetime.datetime.now().strftime("%d.%m.%Y")
    if ticker:
        return f"📊 <b>Разбор дня | {days[weekday]} {date_str}</b>\n🔍 ETH + {ticker}\n\n"
    return f"📅 <b>Итог недели | {date_str}</b>\n\n"


# ─── ГЛАВНАЯ ЛОГИКА ──────────────────────────────────────────────────────────

def main():
    weekday = datetime.datetime.now(datetime.timezone.utc).weekday()
    rotation = ROTATION.get(weekday)

    # Воскресенье — итог недели
    if rotation is None:
        print("📅 Воскресенье — формирую итог недели...")
        weekly_data = fetch_weekly_top()
        eth_data    = fetch_coin_data("ethereum")
        eth_line    = ""
        if eth_data:
            eth_line = (
                f"ETH: ${eth_data['price']:,.2f} "
                f"({eth_data['change_7d']:+.1f}% за 7д)\n"
            )
        prompt = (
            f"{eth_line}{weekly_data}\n\n"
            "Напиши воскресный итог крипторынка за неделю."
        )
        analysis = ask_claude(SYSTEM_WEEKLY, prompt)
        header   = day_header(weekday, None)
        footer   = f"\n\n🔗 Торгуй на BingX 👉 {REF_LINK}"
        send_photo(header + analysis + footer)
        return

    ticker, coin_id, description = rotation

    # Обычный день — ETH + монета дня
    print(f"📊 Формирую разбор ETH + {ticker}...")

    eth_data  = fetch_coin_data("ethereum")
    alt_data  = fetch_coin_data(coin_id)

    if not eth_data or not alt_data:
        print("❌ Не удалось получить данные с CoinGecko")
        sys.exit(1)

    eth_prompt = format_coin_prompt(eth_data, "главный альткоин, индикатор рынка")
    alt_prompt = format_coin_prompt(alt_data, description)

    print("🤖 Запрашиваю AI-анализ ETH...")
    eth_analysis = ask_claude(SYSTEM_PROMPT, eth_prompt)

    print(f"🤖 Запрашиваю AI-анализ {ticker}...")
    alt_analysis = ask_claude(SYSTEM_PROMPT, alt_prompt)

    header = day_header(weekday, ticker)
    eth_section = f"<b>Ξ ETH — ${eth_data['price']:,.2f} ({eth_data['change_24h']:+.1f}%)</b>\n\n{eth_analysis}"
    alt_section = f"\n\n{'─'*20}\n\n<b>{ticker} — ${alt_data['price']:,.4f} ({alt_data['change_24h']:+.1f}%)</b>\n\n{alt_analysis}"
    footer = f"\n\n🔗 Торгуй на BingX 👉 {REF_LINK}"

    full_text = header + eth_section + alt_section + footer

    # Telegram лимит 4096 символов
    if len(full_text) > 4000:
        full_text = full_text[:3950] + "...\n\n🔗 " + REF_LINK

    send_photo(full_text)


if __name__ == "__main__":
    main()

