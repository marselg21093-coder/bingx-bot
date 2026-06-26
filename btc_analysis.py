"""
BTC/USDT Технический анализ
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


def get_btc_ohlcv() -> pd.DataFrame:
    df = yf.download("BTC-USD", period="60d", interval="4h",
                     auto_adjust=True, progress=False)
    df.index.name = "Date"
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    return df[["open", "high", "low", "close", "volume"]].dropna()


def get_col(df, prefix):
    """Найти колонку по префиксу (BBU, BBM, BBL, MACD и т.д.)"""
    cols = [c for c in df.columns if c.startswith(prefix)]
    return cols[0] if cols else None


def calculate_indicators(df: pd.DataFrame) -> dict:
    close = df["close"]

    rsi = ta.rsi(close, length=14).iloc[-1]

    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    macd_val = macd_df[get_col(macd_df, "MACD_")].iloc[-1]
    macd_sig = macd_df[get_col(macd_df, "MACDs_")].iloc[-1]

    bb = ta.bbands(close, length=20, std=2)
    bbu_col = get_col(bb, "BBU")
    bbm_col = get_col(bb, "BBM")
    bbl_col = get_col(bb, "BBL")
    bb_upper = bb[bbu_col].iloc[-1]
    bb_lower = bb[bbl_col].iloc[-1]
    bb_mid   = bb[bbm_col].iloc[-1]

    ema50  = ta.ema(close, length=50).iloc[-1]
    ema200 = ta.ema(close, length=200).iloc[-1]

    price      = close.iloc[-1]
    prev_24h   = close.iloc[-7]
    change_24h = (price - prev_24h) / prev_24h * 100

    support    = round(min(df["low"].tail(20).min(), bb_lower), 0)
    resistance = round(max(df["high"].tail(20).max(), bb_upper), 0)

    return {
        "price": price, "change_24h": change_24h,
        "rsi": rsi, "macd": macd_val, "macd_signal": macd_sig,
        "bb_upper": bb_upper, "bb_lower": bb_lower, "bb_mid": bb_mid,
        "ema50": ema50, "ema200": ema200,
        "support": support, "resistance": resistance,
        "bbu_col": bbu_col, "bbm_col": bbm_col, "bbl_col": bbl_col,
    }


def rsi_label(rsi: float) -> str:
    if rsi >= 70: return "перекупленность ⚠️"
    if rsi <= 30: return "перепроданность ⚠️"
    if rsi >= 60: return "бычий 📈"
    if rsi <= 40: return "медвежий 📉"
    return "нейтральный ↔️"


def overall_signal(ind: dict) -> str:
    score = sum([
        ind["rsi"] > 50,
        ind["macd"] > ind["macd_signal"],
        ind["price"] > ind["ema50"],
        ind["price"] > ind["ema200"],
        ind["price"] > ind["bb_mid"],
    ])
    if score >= 4: return "📈 Бычий"
    if score <= 1: return "📉 Медвежий"
    return "↔️ Нейтральный"


def generate_chart(df: pd.DataFrame, ind: dict) -> BytesIO:
    plot_df    = df.tail(60).copy()
    close      = df["close"]
    bb_data    = ta.bbands(close, length=20, std=2)
    ema50_data = ta.ema(close, length=50)
    rsi_data   = ta.rsi(close, length=14)

    apds = [
        mpf.make_addplot(bb_data[ind["bbu_col"]].tail(60), color="#42A5F5", alpha=0.6, width=0.9),
        mpf.make_addplot(bb_data[ind["bbm_col"]].tail(60), color="#90A4AE", alpha=0.5, width=0.8, linestyle="--"),
        mpf.make_addplot(bb_data[ind["bbl_col"]].tail(60), color="#42A5F5", alpha=0.6, width=0.9),
        mpf.make_addplot(ema50_data.tail(60), color="#FFA726", width=1.3),
        mpf.make_addplot(rsi_data.tail(60), panel=1, color="#CE93D8", width=1.2, ylabel="RSI", secondary_y=False),
    ]

    mc = mpf.make_marketcolors(
        up="#26A69A", down="#EF5350",
        wick={"up": "#26A69A", "down": "#EF5350"},
        edge={"up": "#26A69A", "down": "#EF5350"},
        volume={"up": "#26A69A66", "down": "#EF535066"},
    )
    style = mpf.make_mpf_style(
        marketcolors=mc, base_mpl_style="dark_background",
        gridstyle="--", gridcolor="#2a2a3e",
        facecolor="#0d0d1a", figcolor="#0d0d1a",
        rc={"axes.labelcolor": "#cccccc", "xtick.color": "#aaaaaa",
            "ytick.color": "#aaaaaa", "axes.titlecolor": "#ffffff"},
    )

    buf = BytesIO()
    mpf.plot(
        plot_df, type="candle", style=style, addplot=apds,
        volume=True, panel_ratios=(5, 1, 1), figsize=(13, 8),
        title=f"\nBTC/USDT · 4H · ${ind['price']:,.0f}  ({'+' if ind['change_24h'] >= 0 else ''}{ind['change_24h']:.1f}%)",
        savefig=dict(fname=buf, dpi=130, bbox_inches="tight"),
    )
    buf.seek(0)
    return buf


def build_caption(ind: dict) -> str:
    sign  = "+" if ind["change_24h"] >= 0 else ""
    emoji = "📈" if ind["change_24h"] >= 0 else "📉"
    macd_line  = "бычье пересечение ✅" if ind["macd"] > ind["macd_signal"] else "медвежье пересечение ❌"
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
        f"⚡️ <b>Общий сигнал: {overall_signal(ind)}</b>\n\n"
        f"Торгуй BTC на BingX 👉 {REF_LINK}"
    )


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
