from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import REF_LINK
from handlers.keyboards import back_main_keyboard

def _reg_text() -> str:
    return (
        "📝 <b>Регистрация на BingX</b>\n\n"
        "1. Перейди по ссылке: <a href='{ref}'>BingX — регистрация</a>\n"
        "2. Введи email или номер телефона\n"
        "3. Придумай пароль\n"
        "4. Подтверди email/телефон кодом\n"
        "5. Готово! Аккаунт создан\n\n"
        "💡 Регистрируясь по нашей ссылке, получаешь бонус до $100 и снижение комиссий.\n\n"
        f"👉 <a href='{REF_LINK}'>Зарегистрироваться на BingX</a>"
    ).format(ref=REF_LINK)


def _kyc_text() -> str:
    return (
        "🪪 <b>Верификация KYC</b>\n\n"
        "KYC (Know Your Customer) — обязательная проверка личности.\n\n"
        "<b>Как пройти:</b>\n"
        "1. Войди в аккаунт BingX\n"
        "2. Профиль → Верификация личности\n"
        "3. Выбери страну\n"
        "4. Загрузи паспорт или ID\n"
        "5. Сделай селфи с документом\n"
        "6. Дождись проверки (обычно 1-10 минут)\n\n"
        "<b>Зачем нужен KYC:</b>\n"
        "• Увеличивает лимиты вывода\n"
        "• Открывает доступ к P2P\n"
        "• Обязателен для пополнения через SBP"
    )


def _deposit_text() -> str:
    return (
        "💳 <b>Пополнение счёта на BingX</b>\n\n"
        "<b>Способы пополнения:</b>\n\n"
        "1️⃣ <b>Криптой (быстро)</b>\n"
        "Отправь USDT, BTC, ETH на свой адрес BingX\n\n"
        "2️⃣ <b>P2P (рублями)</b>\n"
        "Купи USDT у других пользователей через встроенный P2P\n\n"
        "3️⃣ <b>SBP (быстро, без P2P)</b>\n"
        "Пополнение через систему быстрых платежей.\n"
        "Нужен KYC и UID. Подробнее — в разделе 🚀 Пополнение SBP\n\n"
        "<b>Минимальный депозит:</b> от $10"
    )


def _futures_text() -> str:
    return (
        "📊 <b>Фьючерсы на BingX</b>\n\n"
        "<b>Как начать торговать фьючерсами:</b>\n\n"
        "1. Войди в приложение BingX\n"
        "2. Вкладка «Фьючерсы» в нижнем меню\n"
        "3. Выбери торговую пару (например BTC/USDT)\n"
        "4. Переведи USDT с основного счёта на фьючерсный\n"
        "5. Выбери плечо (рекомендуем 2-5x для начала)\n"
        "6. Выбери направление: Long (рост) или Short (падение)\n"
        "7. Установи количество и нажми «Открыть позицию»\n\n"
        "⚠️ <b>Всегда ставь стоп-лосс перед входом!</b>\n\n"
        f"👉 <a href='{REF_LINK}'>Открыть BingX</a>"
    )


def _uid_text() -> str:
    return (
        "🔑 <b>Как найти UID на BingX</b>\n\n"
        "UID — уникальный идентификатор твоего аккаунта.\n\n"
        "<b>Где найти:</b>\n"
        "1. Открой приложение BingX\n"
        "2. Нажми на аватар в правом верхнем углу\n"
        "3. В профиле ты увидишь строку «UID: XXXXXXXXXX»\n\n"
        "UID нужен для:\n"
        "• Пополнения через SBP\n"
        "• Идентификации в партнёрской программе\n"
        "• Технической поддержки"
    )


def _promo_text() -> str:
    return (
        "🎁 <b>Промокод и бонус BingX</b>\n\n"
        "При регистрации по нашей ссылке ты получаешь:\n\n"
        "✅ Бонус до $100 на счёт\n"
        "✅ Снижение торговых комиссий\n"
        "✅ Доступ к эксклюзивным акциям\n\n"
        "Промокод применяется автоматически при регистрации по ссылке.\n\n"
        f"👉 <a href='{REF_LINK}'>Зарегистрироваться и получить бонус</a>"
    )


def _ref_text() -> str:
    return (
        "🤝 <b>Партнёрская программа BingX</b>\n\n"
        "Приглашай друзей и получай комиссию с их торговли.\n\n"
        "<b>Как подключиться:</b>\n"
        "1. Войди в BingX\n"
        "2. Профиль → Партнёрская программа\n"
        "3. Получи свою реферальную ссылку\n"
        "4. Делись с друзьями\n\n"
        "<b>Вознаграждение:</b>\n"
        "До 50% от комиссий приглашённых трейдеров пожизненно.\n\n"
        f"👉 <a href='{REF_LINK}'>Открыть BingX</a>"
    )


TOPIC_FUNCS = {
    "bingx_reg":     _reg_text,
    "bingx_kyc":     _kyc_text,
    "bingx_deposit": _deposit_text,
    "bingx_futures": _futures_text,
    "bingx_uid":     _uid_text,
    "bingx_promo":   _promo_text,
    "bingx_ref":     _ref_text,
}

TOPIC_LABELS = {
    "bingx_reg":     "📝 Регистрация",
    "bingx_kyc":     "🪪 KYC верификация",
    "bingx_deposit": "💳 Пополнение счёта",
    "bingx_futures": "📊 Торговля фьючерсами",
    "bingx_uid":     "🔑 Найти UID",
    "bingx_promo":   "🎁 Промокод и бонус",
    "bingx_ref":     "🤝 Партнёрская программа",
}


def bingx_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(label, callback_data=key)]
               for key, label in TOPIC_LABELS.items()]
    buttons.append([InlineKeyboardButton("↩️ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


async def bingx_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "🟦 <b>BingX Assistant</b>\n\n"
        "Всё о работе с биржей BingX.\n"
        "Выбери тему:",
        parse_mode="HTML",
        reply_markup=bingx_menu_keyboard(),
    )


async def bingx_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    key = query.data
    text_fn = TOPIC_FUNCS.get(key)
    if not text_fn:
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ BingX меню",   callback_data="menu_bingx")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")],
    ])
    await query.message.edit_text(
        text_fn(),
        parse_mode="HTML",
        reply_markup=kb,
        disable_web_page_preview=True,
    )
