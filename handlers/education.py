from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from data.lessons import LESSONS
from handlers.keyboards import back_main_keyboard


def lessons_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for i, lesson in enumerate(LESSONS):
        title = lesson["title"].split(": ", 1)[1] if ": " in lesson["title"] else lesson["title"]
        buttons.append([InlineKeyboardButton(f"📚 {title}", callback_data=f"lesson_{i}")])
    buttons.append([InlineKeyboardButton("↩️ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def lesson_keyboard(lesson_idx: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 Пройти тест", callback_data=f"quiz_{lesson_idx}")],
        [InlineKeyboardButton("📚 Все уроки",   callback_data="menu_education")],
        [InlineKeyboardButton("↩️ Главное меню", callback_data="back_main")],
    ])


def quiz_keyboard(lesson_idx: int) -> InlineKeyboardMarkup:
    lesson = LESSONS[lesson_idx]
    buttons = []
    for letter, text in lesson["options"].items():
        buttons.append([InlineKeyboardButton(
            f"{letter}) {text}", callback_data=f"quiz_ans_{lesson_idx}_{letter}"
        )])
    return InlineKeyboardMarkup(buttons)


async def education_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.edit_text(
        "📘 <b>Обучение трейдингу</b>\n\n"
        "10 уроков от основ до риск-менеджмента.\n"
        "После каждого урока — мини-тест.\n\n"
        "Выбери урок:",
        parse_mode="HTML",
        reply_markup=lessons_menu_keyboard(),
    )


async def show_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lesson_idx = int(query.data.split("_")[1])
    lesson = LESSONS[lesson_idx]
    await query.message.edit_text(
        lesson["content"],
        parse_mode="HTML",
        reply_markup=lesson_keyboard(lesson_idx),
    )


async def show_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lesson_idx = int(query.data.split("_")[1])
    lesson = LESSONS[lesson_idx]
    await query.message.edit_text(
        f"🧪 <b>Тест по уроку {lesson_idx + 1}</b>\n\n"
        f"{lesson['quiz_question']}",
        parse_mode="HTML",
        reply_markup=quiz_keyboard(lesson_idx),
    )


async def quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")  # quiz_ans_{idx}_{letter}
    lesson_idx = int(parts[2])
    chosen = parts[3]
    lesson = LESSONS[lesson_idx]
    correct = lesson["correct"]

    if chosen == correct:
        text = (
            f"✅ <b>Правильно!</b>\n\n"
            f"Верный ответ: <b>{correct}) {lesson['options'][correct]}</b>"
        )
    else:
        text = (
            f"❌ <b>Неверно.</b>\n\n"
            f"Твой ответ: {chosen}) {lesson['options'][chosen]}\n"
            f"Правильный ответ: <b>{correct}) {lesson['options'][correct]}</b>"
        )

    # Next lesson button if available
    next_buttons = []
    if lesson_idx + 1 < len(LESSONS):
        next_buttons.append(
            InlineKeyboardButton(
                f"➡️ Урок {lesson_idx + 2}", callback_data=f"lesson_{lesson_idx + 1}"
            )
        )
    kb = InlineKeyboardMarkup([
        next_buttons,
        [InlineKeyboardButton("📚 Все уроки",    callback_data="menu_education")],
        [InlineKeyboardButton("↩️ Главное меню", callback_data="back_main")],
    ])

    await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
