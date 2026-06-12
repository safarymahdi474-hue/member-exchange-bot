from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import aiosqlite
from config import DB_PATH
from database.db import get_setting
from utils.helpers import get_user, add_coins
from keyboards.user_kb import main_menu_kb
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()


async def get_active_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM channels WHERE is_active = 1 ORDER BY added_at ASC"
        ) as cursor:
            return await cursor.fetchall()


async def get_user_joined_channels(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT channel_id FROM user_channel_joins WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


async def show_next_channel(message, user_id: int, bot: Bot, edit: bool = False):
    channels = await get_active_channels()
    joined = await get_user_joined_channels(user_id)
    coins_per_join = await get_setting("coins_per_join")

    next_channel = None
    remaining = 0
    for ch in channels:
        if ch["channel_id"] not in joined:
            if next_channel is None:
                next_channel = ch
            remaining += 1

    if not next_channel:
        text = "✅ آفرین! در تمام کانال‌ها عضو شدی!"
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        if edit:
            await message.edit_text(text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=main_menu_kb())
        return

   kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(
        text=f"➕ عضو شو در {next_channel['channel_name']}",
        url=f"https://t.me/{next_channel['channel_id'].lstrip('@')}"
    )],
    [InlineKeyboardButton(
        text="✔️ عضو شدم، بعدی رو نشون بده",
        callback_data=f"verify_single_{next_channel['channel_id']}"
    )],
    [InlineKeyboardButton(
        text="⏭️ رد کردن این کانال",
        callback_data=f"skip_channel_{next_channel['channel_id']}"
    )]
])

    text = (
        f"📢 کانال {len(joined) + 1} از {len(channels)}\n\n"
        f"🔔 برای دریافت سکه در این کانال عضو شو:\n"
        f"📌 {next_channel['channel_name']}\n\n"
        f"🪙 هر عضویت = {coins_per_join} سکه\n"
        f"📊 {remaining} کانال باقی مانده"
    )

    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.message(F.text == "🎁 عضو شو و سکه بگیر")
async def tasks_handler(message: Message, bot: Bot):
    channels = await get_active_channels()
    if not channels:
        await message.answer("❌ در حال حاضر کانالی برای عضویت وجود ندارد.")
        return
    await show_next_channel(message, message.from_user.id, bot, edit=False)


@router.callback_query(F.data.startswith("verify_single_"))
async def verify_single(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    channel_id = callback.data.replace("verify_single_", "")
    joined_before = await get_user_joined_channels(user_id)
    coins_per_join = await get_setting("coins_per_join")

    if channel_id in joined_before:
        await show_next_channel(callback.message, user_id, bot, edit=True)
        await callback.answer()
        return

    try:
        member = await bot.get_chat_member(channel_id, user_id)
        if member.status in ("member", "administrator", "creator"):
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO user_channel_joins (user_id, channel_id) VALUES (?, ?)",
                    (user_id, channel_id)
                )
                # چک تعداد ممبرهای جذب شده
                async with db.execute(
                    "SELECT quantity FROM orders WHERE channel_id = ? AND status = 'active'",
                    (channel_id,)
                ) as c:
                    order = await c.fetchone()
                async with db.execute(
                    "SELECT COUNT(*) FROM user_channel_joins WHERE channel_id = ?",
                    (channel_id,)
                ) as c:
                    joined_count = (await c.fetchone())[0]
                # اگه به تعداد سفارش رسید کانال رو غیرفعال کن
                if order and joined_count >= order[0]:
                    await db.execute(
                        "UPDATE channels SET is_active = 0 WHERE channel_id = ?",
                        (channel_id,)
                    )
                    await db.execute(
                        "UPDATE orders SET status = 'completed' WHERE channel_id = ? AND status = 'active'",
                        (channel_id,)
                    )
                await db.commit()

            await add_coins(user_id, coins_per_join, "join", f"عضویت در {channel_id}")
            await callback.answer(f"✅ +{coins_per_join} سکه دریافت کردی!", show_alert=True)
            await show_next_channel(callback.message, user_id, bot, edit=True)
        else:
            await callback.answer("❌ هنوز عضو نشدی! اول عضو بشو بعد تأیید کن.", show_alert=True)
    except Exception:
        await callback.answer("❌ خطا در بررسی عضویت. مطمئن شو ربات ادمین کانال باشه.", show_alert=True)
