from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date, timedelta
import aiosqlite
from config import DB_PATH, ADMIN_IDS
from database.db import get_setting, set_setting
from utils.helpers import add_coins, get_all_user_ids
from handlers.user.leaderboard import get_week_start, MEDALS, build_winners_text, get_prizes

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ── ریست هفتگی ────────────────────────────────────────────

async def do_weekly_reset(bot: Bot, announce_to_all: bool = True):
    last_week_start = get_week_start() - timedelta(days=7)
    prizes = await get_prizes()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(
            "SELECT 1 FROM leaderboard_winners WHERE week_start = ? LIMIT 1",
            (last_week_start.isoformat(),)
        ) as c:
            if await c.fetchone():
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

        for board_type, winners in winners_data.items():
            for rank, winner in enumerate(winners, start=1):
                prize = prizes[rank - 1]
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
                await add_coins(
                    winner["user_id"], prize, "leaderboard",
                    f"جایزه لیدربورد {board_type} — رتبه {rank}"
                )
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

    winners_text = await build_winners_text(last_week_start)
    announcement = f"🏆 نتایج لیدربورد هفتگی اعلام شد!\n\n{winners_text}\n\n🔥 هفته جدید شروع شد. بزن بریم!"

    if announce_to_all:
        for uid in await get_all_user_ids():
            try:
                await bot.send_message(uid, announcement)
            except Exception:
                pass

    return True, announcement


# ── پنل مدیریت لیدربورد ───────────────────────────────────

async def leaderboard_panel_text_kb():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    prizes = await get_prizes()
    week_start = get_week_start()

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(DISTINCT user_id) FROM weekly_leaderboard WHERE week_start = ?",
            (week_start.isoformat(),)
        ) as c:
            active_users = (await c.fetchone())[0]

    text = (
        f"🏆 مدیریت لیدربورد\n\n"
        f"📅 هفته جاری از: {week_start.strftime('%Y/%m/%d')}\n"
        f"👥 کاربران فعال این هفته: {active_users} نفر\n\n"
        f"🎁 جوایز فعلی:\n"
        f"  🥇 رتبه اول: {prizes[0]} سکه\n"
        f"  🥈 رتبه دوم: {prizes[1]} سکه\n"
        f"  🥉 رتبه سوم: {prizes[2]} سکه"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 ریست هفتگی + اعلام به همه", callback_data="lb_reset_all")],
        [InlineKeyboardButton(text="📢 پیش‌نمایش نتایج هفته قبل", callback_data="lb_announce_only")],
        [InlineKeyboardButton(text="🥇 جایزه رتبه اول", callback_data="lb_set_prize_1")],
        [InlineKeyboardButton(text="🥈 جایزه رتبه دوم", callback_data="lb_set_prize_2")],
        [InlineKeyboardButton(text="🥉 جایزه رتبه سوم", callback_data="lb_set_prize_3")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_admin")],
    ])
    return text, kb


@router.callback_query(F.data == "admin_leaderboard")
async def admin_leaderboard_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ دسترسی ندارید.", show_alert=True)
    text, kb = await leaderboard_panel_text_kb()
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "lb_reset_all")
async def lb_reset_all(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("⏳ در حال پردازش...")
    success, msg = await do_weekly_reset(bot, announce_to_all=True)
    await callback.message.answer("✅ ریست انجام شد و نتایج به همه اعلام شد." if success else f"⚠️ {msg}")
    await callback.answer()


@router.callback_query(F.data == "lb_announce_only")
async def lb_announce_only(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    last_week_start = get_week_start() - timedelta(days=7)
    text = await build_winners_text(last_week_start)
    await callback.message.answer(f"📢 پیش‌نمایش:\n\n{text}")
    await callback.answer()


# ── ویرایش جوایز ──────────────────────────────────────────

class PrizeStates(StatesGroup):
    waiting_value = State()


PRIZE_MAP = {
    "lb_set_prize_1": ("lb_prize_1", "🥇 جایزه رتبه اول"),
    "lb_set_prize_2": ("lb_prize_2", "🥈 جایزه رتبه دوم"),
    "lb_set_prize_3": ("lb_prize_3", "🥉 جایزه رتبه سوم"),
}


@router.callback_query(F.data.in_(PRIZE_MAP.keys()))
async def set_prize_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    key, label = PRIZE_MAP[callback.data]
    current = await get_setting(key) or {"lb_prize_1": 500, "lb_prize_2": 300, "lb_prize_3": 100}[key]
    await state.update_data(prize_key=key, prize_label=label)
    await callback.message.answer(
        f"{label}\nمقدار فعلی: {current} سکه\n\nمقدار جدید را وارد کن:"
    )
    await state.set_state(PrizeStates.waiting_value)
    await callback.answer()


@router.message(PrizeStates.waiting_value)
async def set_prize_confirm(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ عدد صحیح مثبت وارد کن.")
        return

    data = await state.get_data()
    await set_setting(data["prize_key"], value)
    await message.answer(f"✅ {data['prize_label']} به {value} سکه تغییر یافت.")
    await state.clear()

    # نمایش پنل آپدیت شده
    text, kb = await leaderboard_panel_text_kb()
    await message.answer(text, reply_markup=kb)


# ── دستور مستقیم ──────────────────────────────────────────

@router.message(F.text.startswith("/weekly_reset"))
async def weekly_reset_cmd(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    await message.answer("⏳ در حال پردازش ریست هفتگی...")
    success, msg = await do_weekly_reset(bot, announce_to_all=True)
    await message.answer("✅ ریست هفتگی با موفقیت انجام شد!" if success else f"⚠️ {msg}")
