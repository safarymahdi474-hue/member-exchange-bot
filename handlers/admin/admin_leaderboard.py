from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from datetime import date, timedelta
import aiosqlite
from config import DB_PATH, ADMIN_IDS
from utils.helpers import add_coins, get_all_user_ids
from handlers.user.leaderboard import get_week_start, PRIZES, MEDALS, build_winners_text

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def do_weekly_reset(bot: Bot, announce_to_all: bool = True, announce_to_channel: str = None):
    """
    ریست هفتگی:
    1. برندگان هفته قبل رو پیدا می‌کنه
    2. جایزه می‌ده
    3. اعلام می‌کنه
    4. جدول هفته جدید رو آماده می‌کنه
    """
    last_week_start = get_week_start() - timedelta(days=7)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # چک کن قبلاً ریست شده؟
        async with db.execute(
            "SELECT 1 FROM leaderboard_winners WHERE week_start = ? LIMIT 1",
            (last_week_start.isoformat(),)
        ) as c:
            already_done = await c.fetchone()

        if already_done:
            return False, "این هفته قبلاً ریست شده."

        winners_data = {}
        for board_type in ("coins", "referrals"):
            col = "coins_earned" if board_type == "coins" else "referrals"
            async with db.execute(
                f"""
                SELECT w.user_id, w.{col} as score, u.full_name
                FROM weekly_leaderboard w
                LEFT JOIN users u ON u.user_id = w.user_id
                WHERE w.week_start = ? AND w.{col} > 0
                ORDER BY w.{col} DESC
                LIMIT 3
                """,
                (last_week_start.isoformat(),)
            ) as c:
                winners_data[board_type] = await c.fetchall()

        # ذخیره برندگان و پرداخت جایزه
        for board_type, winners in winners_data.items():
            for rank, winner in enumerate(winners, start=1):
                prize = PRIZES[rank - 1]
                await db.execute(
                    """
                    INSERT OR IGNORE INTO leaderboard_winners
                    (week_start, board_type, rank, user_id, score, prize_coins)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (last_week_start.isoformat(), board_type, rank,
                     winner["user_id"], winner["score"], prize)
                )
                await db.commit()
                # پرداخت سکه
                await add_coins(
                    winner["user_id"], prize, "leaderboard",
                    f"جایزه لیدربورد {board_type} — رتبه {rank}"
                )
                # اطلاع به برنده
                try:
                    medal = MEDALS[rank - 1]
                    board_fa = "سکه" if board_type == "coins" else "رفرال"
                    unit = "سکه" if board_type == "coins" else "رفرال"
                    await bot.send_message(
                        winner["user_id"],
                        f"🎉 تبریک! در لیدربورد هفتگی {board_fa} رتبه {medal} رو گرفتی!\n\n"
                        f"📊 امتیاز تو: {winner['score']} {unit}\n"
                        f"🪙 جایزه: {prize} سکه به حسابت اضافه شد!"
                    )
                except Exception:
                    pass

    # متن اعلام نتایج
    winners_text = await build_winners_text(last_week_start)
    announcement = f"🏆 نتایج لیدربورد هفتگی اعلام شد!\n\n{winners_text}\n\n🔥 هفته جدید شروع شد. بزن بریم!"

    # پیام همگانی به همه کاربران
    if announce_to_all:
        user_ids = await get_all_user_ids()
        sent = 0
        for uid in user_ids:
            try:
                await bot.send_message(uid, announcement)
                sent += 1
            except Exception:
                pass

    # ارسال به کانال ادمین
    if announce_to_channel:
        try:
            await bot.send_message(announce_to_channel, announcement)
        except Exception:
            pass

    return True, announcement


# ── هندلر دستی ادمین ──────────────────────────────────────

@router.callback_query(F.data == "admin_leaderboard")
async def admin_leaderboard_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ دسترسی ندارید.", show_alert=True)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 ریست هفتگی + اعلام به همه", callback_data="lb_reset_all")],
        [InlineKeyboardButton(text="📢 فقط اعلام (بدون ریست)", callback_data="lb_announce_only")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_admin")],
    ])
    week_start = get_week_start()
    last_week = week_start - timedelta(days=7)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(DISTINCT user_id) FROM weekly_leaderboard WHERE week_start = ?",
            (week_start.isoformat(),)
        ) as c:
            active_users = (await c.fetchone())[0]

    await callback.message.answer(
        f"🏆 مدیریت لیدربورد\n\n"
        f"📅 هفته جاری از: {week_start.strftime('%Y/%m/%d')}\n"
        f"👥 کاربران فعال این هفته: {active_users} نفر\n\n"
        f"⚠️ ریست هفتگی باید هر شنبه انجام بشه.",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data == "lb_reset_all")
async def lb_reset_all(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("⏳ در حال پردازش...")
    success, msg = await do_weekly_reset(bot, announce_to_all=True)
    if success:
        await callback.message.answer("✅ ریست انجام شد و نتایج به همه اعلام شد.")
    else:
        await callback.message.answer(f"⚠️ {msg}")
    await callback.answer()


@router.callback_query(F.data == "lb_announce_only")
async def lb_announce_only(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    last_week_start = get_week_start() - timedelta(days=7)
    text = await build_winners_text(last_week_start)
    await callback.message.answer(f"📢 پیش‌نمایش اعلام:\n\n{text}")
    await callback.answer()


# ── دستور مستقیم ──────────────────────────────────────────

@router.message(F.text.startswith("/weekly_reset"))
async def weekly_reset_cmd(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    await message.answer("⏳ در حال پردازش ریست هفتگی...")
    success, msg = await do_weekly_reset(bot, announce_to_all=True)
    if success:
        await message.answer("✅ ریست هفتگی با موفقیت انجام شد!")
    else:
        await message.answer(f"⚠️ {msg}")
