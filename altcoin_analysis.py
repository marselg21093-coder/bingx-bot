"""
Ежедневный разбор альткоинов для @tokenruru
Выходит каждый день в 19:00 МСК
ETH всегда + ротация монеты по дням недели
"""

import os
import sys
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
    5: ("MATIC", "matic-network", "Polygon — Ethereum L2"),
    6: None,  # Воскресенье — итог недели
}

SYSTEM_PROMPT = """
Ты TokenRu AI Terminal — аналитик криптовалютного рынка.
Пишешь ежедневный образовательный разбор монеты для Telegram-канала русскоязычных трейдеров.
Язык: только русский. Используй эмодзи. Структурируй ответ.
Формат:
1. Краткий контекст: что происходит с монетой
2. Тренд (бычий / медвежий / боковик) и почему
3. Ключевые уровни: поддержка и сопротивление
4. На что смотреть сегодня
5. Риски
ВАЖНО: это образовательный анализ, не торговый сигнал.
Заканчивай фразой: «⚠️ Это не торговый сигнал. Проводи собственный анализ перед сделкой.»
Ответ — не более 300 слов.
"""

SYSTEM_WEEKLY = """
Ты TokenRu AI Terminal — аналитик криптовалютного рынка.
Пишешь воскресный итог недели для Telegram-канала русскоязычных трейдеров.
Язык: только русский. Используй эмодзи.
Формат:
1. Настроение рынка за неделю
2. Что выросло и почему
3. Что упало и почему
4. На что смотреть на следующей неделе
5. Главный вывод для трейдера
ВАЖНО: образовательный обзор, не торговые сигналы.
Заканчивай: «⚠️ Это не торговый сигнал. Проводи собственный анализ перед сделкой.»
Ответ — не более 350 слов.
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
        max_tokens=800,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


# ─── ОТПРАВКА ─────────────────────────────────────────────────────────────────

def send_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": CHANNEL_ID, "text": text,
              "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=15,
    )
    result = resp.json()
    if result.get("ok"):
        print("✅ Разбор отправлен")
    else:
        print(f"❌ Ошибка Telegram: {result.get('description')}")
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
        send_message(header + analysis + footer)
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

    send_message(full_text)


if __name__ == "__main__":
    main()
