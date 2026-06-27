"""
TokenRu AI Terminal — главный файл бота
"""
import asyncio
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
from database import init_db

# ─── ХЭНДЛЕРЫ ────────────────────────────────────────────────────────────────
from handlers.start import start
from handlers.common import cancel, back_to_main
from handlers.market import market_handler
from handlers.coin import coin_start, coin_analyze, COIN_TICKER
from handlers.trade_check import (
    trade_start, trade_photo_received, trade_skip_photo, trade_analyze,
    TRADE_PHOTO, TRADE_DETAILS,
)
from handlers.risk import (
    risk_start, risk_deposit, risk_pct, risk_entry, risk_stop, risk_direction,
    DEPOSIT, RISK_PCT, ENTRY, STOP, DIRECTION,
)
from handlers.portfolio import portfolio_start, portfolio_analyze, PORTFOLIO_INPUT
from handlers.mentor import mentor_start, mentor_answer, MENTOR_Q
from handlers.news import news_start, news_analyze, NEWS_INPUT
from handlers.screener import screener_start, screener_run, SCREENER_INPUT
from handlers.education import education_menu, show_lesson, show_quiz, quiz_answer
from handlers.bingx import bingx_menu, bingx_topic, TOPIC_LABELS
from handlers.sbp import sbp_handler
from handlers.profile import (
    profile_handler, profile_set_uid_start, profile_set_uid_save, PROFILE_UID,
)
from handlers.vip import vip_handler
from handlers.admin import grant_vip, revoke_vip, admin_help
from handlers.prediction_vote import handle_group_message, cmd_giveaway

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    fallbacks = [
        CommandHandler("cancel", cancel),
        CallbackQueryHandler(back_to_main, pattern="^back_main$"),
    ]

    # ─── CONVERSATION HANDLERS ────────────────────────────────────────────────
    coin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(coin_start, pattern="^menu_coin$")],
        states={COIN_TICKER: [MessageHandler(filters.TEXT & ~filters.COMMAND, coin_analyze)]},
        fallbacks=fallbacks,
    )

    trade_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(trade_start, pattern="^menu_trade$")],
        states={
            TRADE_PHOTO: [
                MessageHandler(filters.PHOTO, trade_photo_received),
                CommandHandler("skip", trade_skip_photo),
            ],
            TRADE_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, trade_analyze)],
        },
        fallbacks=fallbacks,
    )

    risk_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(risk_start, pattern="^menu_risk$")],
        states={
            DEPOSIT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, risk_deposit)],
            RISK_PCT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, risk_pct)],
            ENTRY:     [MessageHandler(filters.TEXT & ~filters.COMMAND, risk_entry)],
            STOP:      [MessageHandler(filters.TEXT & ~filters.COMMAND, risk_stop)],
            DIRECTION: [CallbackQueryHandler(risk_direction, pattern="^risk_dir_")],
        },
        fallbacks=fallbacks,
    )

    portfolio_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(portfolio_start, pattern="^menu_portfolio$")],
        states={PORTFOLIO_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, portfolio_analyze)]},
        fallbacks=fallbacks,
    )

    mentor_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(mentor_start, pattern="^menu_mentor$")],
        states={MENTOR_Q: [MessageHandler(filters.TEXT & ~filters.COMMAND, mentor_answer)]},
        fallbacks=fallbacks,
    )

    news_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(news_start, pattern="^menu_news$")],
        states={NEWS_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, news_analyze)]},
        fallbacks=fallbacks,
    )

    screener_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(screener_start, pattern="^menu_screener$")],
        states={SCREENER_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, screener_run)]},
        fallbacks=fallbacks,
    )

    profile_uid_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(profile_set_uid_start, pattern="^profile_set_uid$")],
        states={PROFILE_UID: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_set_uid_save)]},
        fallbacks=fallbacks,
    )

    # ─── РЕГИСТРАЦИЯ ─────────────────────────────────────────────────────────

    # Команды
    app.add_handler(CommandHandler("start",      start))
    app.add_handler(CommandHandler("grant_vip",  grant_vip))
    app.add_handler(CommandHandler("revoke_vip", revoke_vip))
    app.add_handler(CommandHandler("admin",      admin_help))
    app.add_handler(CommandHandler("giveaway",   cmd_giveaway))

    # Голосование в группе @tokenru_online (все текстовые сообщения)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_message))

    # Мульти-шаговые диалоги (до простых callback-обработчиков!)
    for conv in [coin_conv, trade_conv, risk_conv, portfolio_conv,
                 mentor_conv, news_conv, screener_conv, profile_uid_conv]:
        app.add_handler(conv)

    # Простые callback-кнопки главного меню
    app.add_handler(CallbackQueryHandler(back_to_main,    pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(market_handler,  pattern="^menu_market$"))
    app.add_handler(CallbackQueryHandler(education_menu,  pattern="^menu_education$"))
    app.add_handler(CallbackQueryHandler(bingx_menu,      pattern="^menu_bingx$"))
    app.add_handler(CallbackQueryHandler(sbp_handler,     pattern="^menu_sbp$"))
    app.add_handler(CallbackQueryHandler(profile_handler, pattern="^menu_profile$"))
    app.add_handler(CallbackQueryHandler(vip_handler,     pattern="^menu_vip$"))

    # Обучение
    app.add_handler(CallbackQueryHandler(show_lesson,  pattern=r"^lesson_\d+$"))
    app.add_handler(CallbackQueryHandler(show_quiz,    pattern=r"^quiz_\d+$"))
    app.add_handler(CallbackQueryHandler(quiz_answer,  pattern=r"^quiz_ans_\d+_[A-D]$"))

    # BingX разделы
    bingx_pattern = "^(" + "|".join(TOPIC_LABELS.keys()) + ")$"
    app.add_handler(CallbackQueryHandler(bingx_topic, pattern=bingx_pattern))

    return app


if __name__ == "__main__":
    logger.info("Инициализация базы данных...")
    asyncio.run(init_db())

    logger.info("Запуск TokenRu AI Terminal...")
    application = build_app()
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
