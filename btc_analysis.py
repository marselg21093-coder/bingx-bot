"""
BTC/USDT Технический анализ
Берёт данные с Yahoo Finance, считает индикаторы, генерирует свечной график
и отправляет в Telegram-канал каждый день в 17:35 МСК
"""

import os
import sys
import requests
import pandas as pd
import mplfinance as mpf
import pandas_ta as ta
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
from io import BytesIO

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = "@tokenruru"
REF_LINK = "https://bingx.com/ru/partner/A888"


# ─── ДАННЫЕ ──────────────────────────────────────────────────────────────────

def get_btc_ohlcv() -> pd.DataFrame:
    """Получить 4H свечи BTC с Yahoo Finance (последние 15 дней)."""
    df = yf.download(
        "BTC-USD",
        period="15d",
        interval="4h",
        auto_adjust=True,
        progress=False,
    )
    df.index.name = "Date"
    df.columns = [c.lower() for c in df.columns]
    return df[["open", "high", "low", "close", "volume"]].dropna()


# ─── ИНДИКАТОРЫ ──────────────────────────────────────────────────────────────

def calculate_indicators(df: pd.DataFrame) -> dict:
    close = df["close"]

    rsi = ta.rsi(close, length=14).iloc[-1]

    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    macd_val = macd_df["MACD_12_26_9"].iloc[-1]
    macd_sig = macd_df["MACDs_12_26_9"].iloc[-1]

    bb = ta.bbands(close, length=20, std=2)
    bb_upper = bb["BBU_20_2.0"].iloc[-1]
    bb_lower = bb["BBL_20_2.0"].iloc[-1]
    bb_mid   = bb["BBM_20_2.0"].iloc[-1]

    ema50  = ta.ema(close, length=50).iloc[-1]
    ema200 = ta.ema(close, length=200).iloc[-1]

    price     = close.iloc[-1]
    prev_24h  = close.iloc[-7]
    change_24h = (price - prev_24h) / prev_24h * 100

    support    = round(min(df["low"].tail(20).min(), bb_lower), 0)
    resistance = round(max(df["high"].tail(20).max(), bb_upper), 0)

    return {
        "price": price,
        "change_24h": change_24h,
        "rsi": rsi,
        "macd": macd_val,
        "macd_signal": macd_sig,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "bb_mid": bb_mid,
        "ema50": ema50,
        "ema200": ema200,
        "support": support,
        "resistance": resistance,
    }


def rsi_label(rsi: float) -> str:
    if rsi >= 70: return "перекупленность ⚠️"
    if rsi <= 30: return "перепроданность ⚠️"
    if rsi >= 60: return "бычий 📈"
    if rsi <= 40: return "медвежий 📉"
    return "нейтральный ↔️"


def overall_signal(ind: dict) -> str:
    score = 0
    if ind["rsi"] > 50:                      score += 1
    if ind["macd"] > ind["macd_signal"]:     score += 1
    if ind["price"] > ind["ema50"]:          score += 1
    if ind["price"] > ind["ema200"]:         score += 1
    if ind["price"] > ind["bb_mid"]:         score += 1
    if score >= 4: return "📈 Бычий"
    if score <= 1: return "📉 Медвежий"
    return "↔️ Нейтральный"


# ─── ГРАФИК ──────────────────────────────────────────────────────────────────

def generate_chart(df: pd.DataFrame, ind: dict) -> BytesIO:
    plot_df = df.tail(60).copy()
    close   = df["close"]

    bb_data    = ta.bbands(close, length=20, std=2)
    ema50_data = ta.ema(close, length=50)
    rsi_data   = ta.rsi(close, length=14)

    apds = [
        mpf.make_addplot(bb_data["BBU_20_2.0"].tail(60),
                         color="#42A5F5", alpha=0.6, width=0.9),
        mpf.make_addplot(bb_data["BBM_20_2.0"].tail(60),
                         color="#90A4AE", alpha=0.5, width=0.8, linestyle="--"),
        mpf.make_addplot(bb_data["BBL_20_2.0"].tail(60),
                         color="#42A5F5", alpha=0.6, width=0.9),
        mpf.make_addplot(ema50_data.tail(60),
                         color="#FFA726", width=1.3, label="EMA50"),
        mpf.make_addplot(rsi_data.tail(60),
                         panel=1, color="#CE93D8", width=1.2,
                         ylabel="RSI", secondary_y=False),
    ]

    mc = mpf.make_marketcolors(
        up="#26A69A", down="#EF5350",
        wick={"up": "#26A69A", "down": "#EF5350"},
        edge={"up": "#26A69A", "down": "#EF5350"},
        volume={"up": "#26A69A66", "down": "#EF535066"},
    )
    style = mpf.make_mpf_style(
        marketcolors=mc,
        base_mpl_style="dark_background",
        gridstyle="--",
        gridcolor="#2a2a3e",
        facecolor="#0d0d1a",
        figcolor="#0d0d1a",
        rc={"axes.labelcolor": "#cccccc", "xtick.color": "#aaaaaa",
            "ytick.color": "#aaaaaa", "axes.titlecolor": "#ffffff"},
    )

    buf = BytesIO()
    mpf.plot(
        plot_df,
        type="candle",
        style=style,
        addplot=apds,
        volume=True,
        panel_ratios=(5, 1, 1),
        figsize=(13, 8),
        title=f"\nBTC/USDT · 4H · ${ind['price']:,.0f}  ({'+' if ind['change_24h'] >= 0 else ''}{ind['change_24h']:.1f}%)",
        savefig=dict(fname=buf, dpi=130, bbox_inches="tight"),
    )
    buf.seek(0)
    return buf


# ─── ТЕКСТ АНАЛИЗА ───────────────────────────────────────────────────────────

def build_caption(ind: dict) -> str:
    sign   = "+" if ind["change_24h"] >= 0 else ""
    emoji  = "📈" if ind["change_24h"] >= 0 else "📉"
    signal = overall_signal(ind)

    macd_line = (
        "бычье пересечение ✅" if ind["macd"] > ind["macd_signal"]
        else "медвежье пересечение ❌"
    )
    ema50_line  = f"${ind['ema50']:,.0f}  {'✅ выше' if ind['price'] > ind['ema50']  else '❌ ниже'}"
    ema200_line = f"${ind['ema200']:,.0f} {'✅ выше' if ind['price'] > ind['ema200'] else '❌ ниже'}"

    return (
        f"📊 <b>BTC/USDT — Технический анализ (4H)</b>\n\n"
        f"💰 Цена: <b>${ind['price']:,.0f}</b>\n"
        f"{emoji} За 24ч: <b>{sign}{ind['change_24h']:.1f}%</b>\n\n"
        f"📉 <b>Индикаторы:</b>\n"
        f"• RSI (14): <b>{ind['rsi']:.1f}</b> — {rsi_label(ind['rsi'])}\n"
        f"• MACD: {macd_line}\n"
        f"• Bollinger Bands: ${ind['bb_lower']:,.0f} – ${ind['bb_upper']:,.0f}\n"
        f"• EMA 50:  {ema50_line}\n"
        f"• EMA 200: {ema200_line}\n\n"
        f"🎯 <b>Уровни:</b>\n"
        f"• Поддержка:    <b>${ind['support']:,.0f}</b>\n"
        f"• Сопротивление: <b>${ind['resistance']:,.0f}</b>\n\n"
        f"⚡️ <b>Общий сигнал: {signal}</b>\n\n"
        f"Торгуй BTC на BingX 👉 {REF_LINK}"
    )


# ─── ОТПРАВКА ─────────────────────────────────────────────────────────────────

def send_analysis(buf: BytesIO, caption: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    resp = requests.post(
        url,
        data={"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"},
        files={"photo": ("btc_chart.png", buf, "image/png")},
        timeout=30,
    )
    result = resp.json()
    if result.get("ok"):
        print("✅ Анализ BTC отправлен в канал")
    else:
        print(f"❌ Ошибка Telegram: {result.get('description')}")
        sys.exit(1)


# ─── ЗАПУСК ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("📥 Получаю данные BTC с Yahoo Finance...")
    df = get_btc_ohlcv()

    print("🔢 Считаю индикаторы...")
    ind = calculate_indicators(df)

    print("🎨 Генерирую график...")
    chart_buf = generate_chart(df, ind)

    caption = build_caption(ind)
    print(caption)

    print("📤 Отправляю в Telegram...")
    send_analysis(chart_buf, caption)
