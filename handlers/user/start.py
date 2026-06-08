from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart
from config import ADMIN_IDS
from database.db import get_setting
from utils.helpers import get_user, create_user, get_referral_count
from keyboards.user_kb import main_menu_kb

router = Router()

MUST_JOIN_CHANNEL = "@exchange_management"  # آیدی کانال خودت رو اینجا بنویس


async def check_membership(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(MUST_JOIN_CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""

    # چک عضویت اجباری
    is_member = await check_membership(bot, user_id)
    if not is_member:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="➕ عضو شو در کانال ما",
                url=f"https://t.me/{MUST_JOIN_CHANNEL.lstrip('@')}"
            )],
            [InlineKeyboardButton(
                text="✔️ عضو شدم",
                callback_data=f"check_join_start_{message.text}"
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


@router.callback_query(F.data.startswith("check_join_start_"))
async def check_join_start(callback, bot: Bot):
    user_id = callback.from_user.id
    is_member = await check_membership(bot, user_id)
    if not is_member:
        await callback.answer("❌ هنوز عضو نشدی!", show_alert=True)
        return
    original_text = callback.data.replace("check_join_start_", "")
    await callback.message.delete()
    # شبیه‌سازی دوباره start
    callback.message.text = original_text
    await cmd_start(callback.message, bot)
    await callback.answer()
