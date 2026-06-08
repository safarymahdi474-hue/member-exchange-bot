from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from config import ADMIN_IDS
from utils.helpers import get_user, get_referral_count, get_coin_history
from keyboards.user_kb import profile_kb, main_menu_kb
from keyboards.admin_kb import admin_profile_kb

router = Router()


async def show_profile(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await message.answer("ابتدا /start بزن.")
        return

    referral_count = await get_referral_count(user_id)
    is_admin = user_id in ADMIN_IDS

    text = (
        f"👤 پروفایل {'ادمین' if is_admin else 'شما'}\n\n"
        f"🪙 موجودی سکه: {user['coins']} سکه\n"
        f"👥 تعداد رفرال‌ها: {referral_count} نفر\n"
        f"🔗 لینک دعوت: t.me/{(await message.bot.get_me()).username}?start={user_id}\n"
        f"📅 تاریخ عضویت: {str(user['joined_at'])[:10]}\n"
    )
    if is_admin:
        text += f"🛡️ سطح دسترسی: ادمین\n"

    kb = admin_profile_kb() if is_admin else profile_kb()
    await message.answer(text, reply_markup=kb)


@router.message(F.text == "👤 پروفایل")
async def profile_handler(message: Message):
    await show_profile(message)


@router.callback_query(F.data == "history")
async def history_handler(callback: CallbackQuery):
    history = await get_coin_history(callback.from_user.id)
    if not history:
        await callback.answer("تاریخچه‌ای وجود ندارد.", show_alert=True)
        return

    type_labels = {
        "start": "🎁 هدیه شروع",
        "join": "✅ عضویت کانال",
        "referral": "👥 رفرال",
        "order": "📦 سفارش ممبر",
        "transfer_in": "💸 دریافت سکه",
        "transfer_out": "💸 ارسال سکه",
        "gift_code": "🎟️ کد هدیه",
        "admin": "🛡️ ادمین",
    }

    lines = ["📊 تاریخچه ۲۰ تراکنش اخیر:\n"]
    for tx in history:
        label = type_labels.get(tx["type"], tx["type"])
        sign = "+" if tx["amount"] > 0 else ""
        lines.append(f"{label}: {sign}{tx['amount']} سکه\n📝 {tx['description'] or '-'}\n🕐 {str(tx['created_at'])[:16]}\n")

    await callback.message.answer("\n".join(lines))
    await callback.answer()
