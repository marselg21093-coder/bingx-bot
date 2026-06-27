import aiosqlite
import datetime
from config import DB_PATH, FREE_DAILY_LIMIT


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id         INTEGER PRIMARY KEY,
                username        TEXT,
                first_name      TEXT,
                registered_at   TEXT NOT NULL,
                is_vip          INTEGER DEFAULT 0,
                bingx_uid       TEXT,
                requests_today  INTEGER DEFAULT 0,
                requests_date   TEXT    DEFAULT '',
                total_requests  INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS prediction_votes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                date         TEXT,
                user_id      INTEGER,
                username     TEXT,
                first_name   TEXT,
                vote         TEXT,
                voted_at     TEXT,
                is_correct   INTEGER DEFAULT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS prediction_streaks (
                user_id           INTEGER PRIMARY KEY,
                username          TEXT,
                first_name        TEXT,
                current_streak    INTEGER DEFAULT 0,
                max_streak        INTEGER DEFAULT 0,
                total_correct     INTEGER DEFAULT 0,
                last_correct_date TEXT,
                giveaway_round    INTEGER DEFAULT 0
            )
        """)
        await db.commit()


# ─── USERS ────────────────────────────────────────────────────────────────────

async def get_or_create_user(user_id: int, username: str, first_name: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            now = datetime.datetime.now().isoformat()
            await db.execute(
                "INSERT INTO users (user_id, username, first_name, registered_at) VALUES (?, ?, ?, ?)",
                (user_id, username or "", first_name or "", now),
            )
            await db.commit()
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
        return dict(row)


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None


async def can_make_request(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user:
        return True
    if user["is_vip"]:
        return True
    today = datetime.date.today().isoformat()
    if user["requests_date"] != today:
        return True
    return user["requests_today"] < FREE_DAILY_LIMIT


async def increment_requests(user_id: int) -> None:
    today = datetime.date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        user = await get_user(user_id)
        if not user:
            return
        if user["requests_date"] != today:
            await db.execute(
                "UPDATE users SET requests_today = 1, requests_date = ?, total_requests = total_requests + 1 WHERE user_id = ?",
                (today, user_id),
            )
        else:
            await db.execute(
                "UPDATE users SET requests_today = requests_today + 1, total_requests = total_requests + 1 WHERE user_id = ?",
                (user_id,),
            )
        await db.commit()


async def get_requests_left(user_id: int) -> int:
    user = await get_user(user_id)
    if not user or user["is_vip"]:
        return -1
    today = datetime.date.today().isoformat()
    if user["requests_date"] != today:
        return FREE_DAILY_LIMIT
    return max(0, FREE_DAILY_LIMIT - user["requests_today"])


async def set_vip(user_id: int, is_vip: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_vip = ? WHERE user_id = ?",
            (1 if is_vip else 0, user_id),
        )
        await db.commit()


async def set_bingx_uid(user_id: int, uid: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET bingx_uid = ? WHERE user_id = ?", (uid, user_id))
        await db.commit()


# ─── PREDICTION VOTES ─────────────────────────────────────────────────────────

async def save_vote(date: str, user_id: int, username: str, first_name: str, vote: str) -> bool:
    """Сохраняет голос. Возвращает False если уже голосовал сегодня."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM prediction_votes WHERE date = ? AND user_id = ?",
            (date, user_id),
        ) as cur:
            existing = await cur.fetchone()
        if existing:
            return False
        now = datetime.datetime.now().isoformat()
        await db.execute(
            "INSERT INTO prediction_votes (date, user_id, username, first_name, vote, voted_at) VALUES (?,?,?,?,?,?)",
            (date, user_id, username or "", first_name or "", vote, now),
        )
        await db.commit()
        return True


async def get_votes_for_date(date: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM prediction_votes WHERE date = ?", (date,)
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def mark_votes_result(date: str, correct_vote: str) -> list[dict]:
    """Помечает голоса как верные/неверные, возвращает список победителей."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE prediction_votes SET is_correct = CASE WHEN vote = ? THEN 1 ELSE 0 END WHERE date = ?",
            (correct_vote, date),
        )
        await db.commit()
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM prediction_votes WHERE date = ? AND is_correct = 1", (date,)
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]


# ─── STREAKS ──────────────────────────────────────────────────────────────────

async def update_streak(user_id: int, username: str, first_name: str, correct: bool, date: str) -> dict:
    """Обновляет серию пользователя. Возвращает актуальные данные."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM prediction_streaks WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()

        if row is None:
            streak = 1 if correct else 0
            max_s  = streak
            total  = 1 if correct else 0
            giveaway = 1 if streak >= 7 else 0
            await db.execute(
                """INSERT INTO prediction_streaks
                   (user_id, username, first_name, current_streak, max_streak,
                    total_correct, last_correct_date, giveaway_round)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (user_id, username or "", first_name or "", streak, max_s,
                 total, date if correct else None, giveaway),
            )
        else:
            data = dict(row)
            if correct:
                streak = data["current_streak"] + 1
                total  = data["total_correct"] + 1
                max_s  = max(data["max_streak"], streak)
                last_d = date
            else:
                streak = 0
                total  = data["total_correct"]
                max_s  = data["max_streak"]
                last_d = data["last_correct_date"]

            giveaway = 1 if streak >= 7 else data["giveaway_round"]
            await db.execute(
                """UPDATE prediction_streaks
                   SET username = ?, first_name = ?, current_streak = ?,
                       max_streak = ?, total_correct = ?, last_correct_date = ?,
                       giveaway_round = ?
                   WHERE user_id = ?""",
                (username or "", first_name or "", streak, max_s,
                 total, last_d, giveaway, user_id),
            )

        await db.commit()
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM prediction_streaks WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        return dict(row)


async def get_giveaway_participants() -> list[dict]:
    """Все участники розыгрыша (серия >= 7)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM prediction_streaks WHERE giveaway_round = 1 ORDER BY current_streak DESC"
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def reset_giveaway() -> None:
    """Сбрасывает флаг розыгрыша после его проведения."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE prediction_streaks SET giveaway_round = 0")
        await db.commit()
