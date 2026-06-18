from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite
from datetime import date, timedelta
from config import DB_PATH

router = Router()

MEDALS = ["🥇", "🥈", "🥉"]
PRIZES = [500, 300, 100]


def get_week_start() -> date:
    """شنبه این هفته"""
    today = date.today()
    # weekday(): Mon=0 ... Sat=5, Sun=6  →  شنبه = Sat = 5
    days_since_saturday = (today.weekday() - 5) % 7
    return today - timedelta(days=days_since_saturday)


def leaderboard_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🪙 سکه", callback_data="lb_coins"),
            InlineKeyboardButton(text="👥 رفرال", callback_data="lb_referrals"),
        ],
        [InlineKeyboardButton(text="🏆 برندگان هفته قبل", callback_data="lb_last_week")],
    ])


async def build_board_text(board_type: str, week_start: date, title: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        col = "coins_earned" if board_type == "coins" else "referrals"
        async with db.execute(
            f"""
            SELECT w.user_id, w.{col} as score, u.full_name
            FROM weekly_leaderboard w
            LEFT JOIN users u ON u.user_id = w.user_id
            WHERE w.week_start = ? AND w.{col} > 0
            ORDER BY w.{col} DESC
            LIMIT 10
            """,
            (week_start.isoformat(),)
        ) as c:
            rows = await c.fetchall()

    week_end = week_start + timedelta(days=6)
    lines = [
        f"🏆 {title}",
        f"📅 هفته {week_start.strftime('%m/%d')} تا {week_end.strftime('%m/%d')}\n",
        f"🎁 جوایز: {PRIZES[0]}🥇 | {PRIZES[1]}🥈 | {PRIZES[2]}🥉 سکه\n",
    ]

    if not rows:
        lines.append("هنوز کسی امتیاز نگرفته!\nاول باش 🚀")
    else:
        unit = "سکه" if board_type == "coins" else "رفرال"
        for i, row in enumerate(rows):
            medal = MEDALS[i] if i < 3 else f"{i+1}."
            name = row["full_name"] or f"کاربر {row['user_id']}"
            lines.append(f"{medal} {name} — {row['score']} {unit}")

    return "\n".join(lines)


async def build_winners_text(week_start: date) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT lw.*, u.full_name
            FROM leaderboard_winners lw
            LEFT JOIN users u ON u.user_id = lw.user_id
            WHERE lw.week_start = ?
            ORDER BY lw.board_type, lw.rank
            """,
            (week_start.isoformat(),)
        ) as c:
            rows = await c.fetchall()

    if not rows:
        return "❌ نتیجه‌ای برای هفته قبل ثبت نشده."

    week_end = week_start + timedelta(days=6)
    lines = [f"🏆 برندگان هفته {week_start.strftime('%m/%d')} تا {week_end.strftime('%m/%d')}\n"]

    coins_rows = [r for r in rows if r["board_type"] == "coins"]
    ref_rows = [r for r in rows if r["board_type"] == "referrals"]

    if coins_rows:
        lines.append("🪙 بیشترین سکه:")
        for r in coins_rows:
            medal = MEDALS[r["rank"] - 1]
            name = r["full_name"] or f"کاربر {r['user_id']}"
            lines.append(f"  {medal} {name} — {r['score']} سکه (+{r['prize_coins']} جایزه)")

    if ref_rows:
        lines.append("\n👥 بیشترین رفرال:")
        for r in ref_rows:
            medal = MEDALS[r["rank"] - 1]
            name = r["full_name"] or f"کاربر {r['user_id']}"
            lines.append(f"  {medal} {name} — {r['score']} رفرال (+{r['prize_coins']} جایزه)")

    return "\n".join(lines)


# ── هندلرها ──────────────────────────────────────────────

@router.message(F.text == "🏆 لیدربورد")
async def leaderboard_menu(message: Message):
    week_start = get_week_start()
    text = await build_board_text("coins", week_start, "لیدربورد هفتگی — سکه")
    await message.answer(text, reply_markup=leaderboard_kb())


@router.callback_query(F.data == "lb_coins")
async def lb_coins(callback: CallbackQuery):
    week_start = get_week_start()
    text = await build_board_text("coins", week_start, "لیدربورد هفتگی — سکه")
    await callback.message.edit_text(text, reply_markup=leaderboard_kb())
    await callback.answer()


@router.callback_query(F.data == "lb_referrals")
async def lb_referrals(callback: CallbackQuery):
    week_start = get_week_start()
    text = await build_board_text("referrals", week_start, "لیدربورد هفتگی — رفرال")
    await callback.message.edit_text(text, reply_markup=leaderboard_kb())
    await callback.answer()


@router.callback_query(F.data == "lb_last_week")
async def lb_last_week(callback: CallbackQuery):
    last_week_start = get_week_start() - timedelta(days=7)
    text = await build_winners_text(last_week_start)
    await callback.message.edit_text(text, reply_markup=leaderboard_kb())
    await callback.answer()
