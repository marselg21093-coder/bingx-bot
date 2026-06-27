from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Анализ рынка",      callback_data="menu_market"),
            InlineKeyboardButton("🪙 Анализ монеты",     callback_data="menu_coin"),
        ],
        [
            InlineKeyboardButton("📸 Проверка сделки",   callback_data="menu_trade"),
            InlineKeyboardButton("⚖️ Риск-менеджер",     callback_data="menu_risk"),
        ],
        [
            InlineKeyboardButton("💼 Анализ портфеля",   callback_data="menu_portfolio"),
            InlineKeyboardButton("🧠 AI-наставник",      callback_data="menu_mentor"),
        ],
        [
            InlineKeyboardButton("📰 Разбор новостей",   callback_data="menu_news"),
            InlineKeyboardButton("🔍 Поиск монет",       callback_data="menu_screener"),
        ],
        [
            InlineKeyboardButton("📘 Обучение",          callback_data="menu_education"),
            InlineKeyboardButton("🟦 BingX Assistant",   callback_data="menu_bingx"),
        ],
        [
            InlineKeyboardButton("🚀 Пополнение SBP",    callback_data="menu_sbp"),
            InlineKeyboardButton("👤 Мой профиль",       callback_data="menu_profile"),
        ],
        [
            InlineKeyboardButton("💎 VIP-доступ",        callback_data="menu_vip"),
        ],
    ])


def back_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("↩️ Главное меню", callback_data="back_main")
    ]])
