from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
import aiosqlite
from config import ADMIN_IDS, DB_PATH
from database.db import get_setting
from utils.helpers import get_user, create_user
from keyboards.user_kb import main_menu_kb

router = Router()


async def get_unjoin_channel(bot: Bot, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # حذف کانال‌های منقضی شده
        await db.execute(
            "UPDATE force_join_channels SET is_active = 0 "
            "WHERE remove_type = 'time' AND expires_at < datetime('now')"
        )
        await db.commit()
        async with db.execute(
            "SELECT * FROM force_join_channels WHERE is_active = 1"
        ) as c:
            channels = await c.fetchall()

    for ch in channels:
        try:
            member = await bot.get_chat_member(ch["channel_id"], user_id)
            if member.status not in ("member", "administrator", "creator"):
                return ch
        except Exception:
            pass
    return None


async def update_force_join_count(channel_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE force_join_channels SET current_count = current_count + 1 "
            "WHERE channel_id = ?", (channel_id,)
        )
        # اگه به تعداد هدف رسید غیرفعالش کن
        await db.execute(
            "UPDATE force_join_channels SET is_active = 0 "
            "WHERE channel_id = ? AND remove_type = 'count' "
            "AND current_count >= remove_value",
            (channel_id,)
        )
        await db.commit()


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""

    # چک عضویت اجباری
    unjoin = await get_unjoin_channel(bot, user_id)
    if unjoin:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"➕ عضو شو در {unjoin['channel_name']}",
                url=f"https://t.me/{unjoin['channel_id'].lstrip('@')}"
            )],
            [InlineKeyboardButton(
                text="✔️ عضو شدم",
                callback_data=f"check_force_join_{message.text}"
            )]
        ])
        await message.answer(
            "⚠️ برای استفاده از ربات باید ابتدا در کانال ما عضو بشی:",
            reply_markup=kb
        )
        return

    # بررسی رفرال
    referrer_id = None
    args = message.text.split()
    if len(args) > 1:
        try:
            ref_id = int(args[1])
            if ref_id != user_id:
                referrer_id = ref_id
        except ValueError:
            pass

    existing = await get_user(user_id)
    if not existing:
        await create_user(user_id, username, full_name, referrer_id)
        start_coins = await get_setting("coins_start")

        # آپدیت شمارنده کانال اجباری
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT channel_id FROM force_join_channels WHERE is_active = 1"
            ) as c:
                force_channels = await c.fetchall()
        for ch in force_channels:
            try:
                member = await bot.get_chat_member(ch["channel_id"], user_id)
                if member.status in ("member", "administrator", "creator"):
                    await update_force_join_count(ch["channel_id"])
            except Exception:
                pass

        await message.answer(
            f"👋 خوش اومدی {full_name}!\n\n"
            f"🪙 {start_coins} سکه به عنوان هدیه شروع به حسابت اضافه شد.\n\n"
            f"از منو پایین شروع کن 👇",
            reply_markup=main_menu_kb()
        )

        # اطلاع به صاحب لینک رفرال
        if referrer_id:
            try:
                await bot.send_message(
                    referrer_id,
                    f"🎉 کاربر {full_name} (@{username}) با لینک دعوت تو ربات رو شروع کرد!\n"
                    f"🪙 ۲۵ سکه به حسابت اضافه شد."
                )
            except Exception:
                pass
    else:
        await message.answer("👋 خوش برگشتی!", reply_markup=main_menu_kb())


@router.callback_query(F.data.startswith("check_force_join_"))
async def check_force_join(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    unjoin = await get_unjoin_channel(bot, user_id)
    if unjoin:
        await callback.answer("❌ هنوز عضو نشدی!", show_alert=True)
        return
    original_text = callback.data.replace("check_force_join_", "")
    await callback.message.delete()
    callback.message.text = original_text
    await cmd_start(callback.message, bot)
    await callback.answer()
