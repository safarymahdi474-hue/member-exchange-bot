from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
import aiosqlite
from config import DB_PATH
from database.db import get_setting
from utils.helpers import get_user, add_coins
from keyboards.user_kb import channels_kb, main_menu_kb

router = Router()


async def get_active_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM channels WHERE is_active = 1") as cursor:
            return await cursor.fetchall()


async def get_user_joined_channels(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT channel_id FROM user_channel_joins WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


@router.message(F.text == "🎁 عضو شو و سکه بگیر")
async def tasks_handler(message: Message):
    channels = await get_active_channels()
    if not channels:
        await message.answer("❌ در حال حاضر کانالی برای عضویت وجود ندارد.")
        return

    joined = await get_user_joined_channels(message.from_user.id)
    coins_per_join = await get_setting("coins_per_join")

    await message.answer(
        f"📢 برای دریافت سکه در کانال‌های زیر عضو شو:\n"
        f"🪙 هر عضویت = {coins_per_join} سکه\n\n"
        f"بعد از عضو شدن دکمه ✔️ تأیید عضویت‌ها رو بزن:",
        reply_markup=channels_kb([dict(ch) for ch in channels], joined)
    )


@router.callback_query(F.data == "verify_joins")
async def verify_joins(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    channels = await get_active_channels()
    joined_before = await get_user_joined_channels(user_id)
    coins_per_join = await get_setting("coins_per_join")

    earned = 0
    new_joins = []

    for ch in channels:
        ch_id = ch["channel_id"]
        if ch_id in joined_before:
            continue
        try:
            member = await bot.get_chat_member(ch_id, user_id)
            if member.status in ("member", "administrator", "creator"):
                new_joins.append(ch_id)
                earned += coins_per_join
        except Exception:
            pass

    if new_joins:
        async with aiosqlite.connect(DB_PATH) as db:
            for ch_id in new_joins:
                await db.execute(
                    "INSERT OR IGNORE INTO user_channel_joins (user_id, channel_id) VALUES (?, ?)",
                    (user_id, ch_id)
                )
            await db.commit()
        await add_coins(user_id, earned, "join", f"عضویت در {len(new_joins)} کانال")
        await callback.answer(f"✅ {len(new_joins)} عضویت تأیید شد! +{earned} سکه دریافت کردی.", show_alert=True)
    else:
        await callback.answer("⚠️ عضویت جدیدی یافت نشد.", show_alert=True)

    # آپدیت کیبورد
    joined_all = await get_user_joined_channels(user_id)
    await callback.message.edit_reply_markup(
        reply_markup=channels_kb([dict(ch) for ch in channels], joined_all)
    )
