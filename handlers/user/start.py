from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from config import ADMIN_IDS
from database.db import get_setting
from utils.helpers import get_user, create_user, get_referral_count
from keyboards.user_kb import main_menu_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""

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
        user = await get_user(user_id)
        start_coins = await get_setting("coins_start")
        await message.answer(
            f"👋 خوش اومدی {full_name}!\n\n"
            f"🪙 {start_coins} سکه به عنوان هدیه شروع به حسابت اضافه شد.\n\n"
            f"از منو پایین شروع کن 👇",
            reply_markup=main_menu_kb()
        )
    else:
        await message.answer("👋 خوش برگشتی!", reply_markup=main_menu_kb())
