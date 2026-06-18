import aiosqlite
from datetime import date, timedelta
from config import DB_PATH
from database.db import get_setting


# ── لیدربورد هلپر ─────────────────────────────────────────

def get_week_start() -> date:
    today = date.today()
    days_since_saturday = (today.weekday() - 5) % 7
    return today - timedelta(days=days_since_saturday)


async def update_leaderboard_coins(user_id: int, amount: int):
    """فقط وقتی سکه مثبت گرفته می‌شه (نه خرج)"""
    if amount <= 0:
        return
    week_start = get_week_start()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO weekly_leaderboard (week_start, user_id, coins_earned)
            VALUES (?, ?, ?)
            ON CONFLICT(week_start, user_id) DO UPDATE SET
            coins_earned = coins_earned + excluded.coins_earned
            """,
            (week_start.isoformat(), user_id, amount)
        )
        await db.commit()


async def update_leaderboard_referral(referrer_id: int):
    """وقتی کاربر جدید با لینک رفرال میاد"""
    week_start = get_week_start()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO weekly_leaderboard (week_start, user_id, referrals)
            VALUES (?, ?, 1)
            ON CONFLICT(week_start, user_id) DO UPDATE SET
            referrals = referrals + 1
            """,
            (week_start.isoformat(), referrer_id)
        )
        await db.commit()


# ── هلپرهای اصلی ──────────────────────────────────────────

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()


async def create_user(user_id: int, username: str, full_name: str, referrer_id: int = None):
    start_coins = await get_setting("coins_start")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name, coins, referrer_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, full_name, start_coins, referrer_id)
        )
        await db.commit()

        if referrer_id:
            referral_coins = await get_setting("coins_per_referral")
            await add_coins(referrer_id, referral_coins, "referral", f"رفرال کاربر {user_id}")
            # آپدیت لیدربورد رفرال
            await update_leaderboard_referral(referrer_id)


async def add_coins(user_id: int, amount: int, tx_type: str, description: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
        await db.execute(
            "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
            (user_id, amount, tx_type, description)
        )
        await db.commit()

    # آپدیت لیدربورد سکه (فقط سکه‌های کسب‌شده، نه جایزه لیدربورد خودش)
    if amount > 0 and tx_type not in ("leaderboard", "admin"):
        await update_leaderboard_coins(user_id, amount)


async def deduct_coins(user_id: int, amount: int, tx_type: str, description: str = "") -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] < amount:
                return False
        await db.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (amount, user_id))
        await db.execute(
            "INSERT INTO coin_transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)",
            (user_id, -amount, tx_type, description)
        )
        await db.commit()
        return True


async def get_referral_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_coin_history(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM coin_transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()


async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]
