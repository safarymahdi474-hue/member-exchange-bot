from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS
from keyboards.user_kb import main_menu_kb, back_kb

router = Router()

DONATE_LINK = "https://daramet.com/member_exchange"


class DonateStates(StatesGroup):
    waiting_receipt = State()


@router.callback_query(F.data == "buy_coins")
async def buy_coins_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        f"💰 خرید سکه\n\n"
        f"🔗 لینک پرداخت:\n{DONATE_LINK}\n\n"
        f"📌 راهنما:\n"
        f"۱. روی لینک بالا برو و مبلغ دلخواه رو پرداخت کن\n"
        f"۲. بعد از پرداخت، عکس فیش رو اینجا بفرست\n"
        f"۳. بعد از تأیید ادمین، سکه به حسابت اضافه میشه\n\n"
        f"💡 نرخ تبدیل: هر ۱۰۰۰ تومان = ۱ سکه\n\n"
        f"📸 عکس فیش رو ارسال کن:",
        reply_markup=back_kb()
    )
    await state.set_state(DonateStates.waiting_receipt)
    await callback.answer()


@router.message(DonateStates.waiting_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username or "ندارد"
    full_name = message.from_user.full_name or ""

    # ارسال به همه ادمین‌ها
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                admin_id,
                photo=message.photo[-1].file_id,
                caption=(
                    f"💰 درخواست خرید سکه\n\n"
                    f"👤 نام: {full_name}\n"
                    f"🆔 آیدی: {user_id}\n"
                    f"👤 یوزرنیم: @{username}\n\n"
                    f"برای دادن سکه از دستور زیر استفاده کن:\n"
                    f"/addscore {user_id} [تعداد سکه]"
                )
            )
        except Exception:
            pass

    await message.answer(
        "✅ فیش شما ارسال شد!\n\n"
        "⏳ بعد از تأیید ادمین، سکه به حسابت اضافه میشه.",
        reply_markup=main_menu_kb()
    )
    await state.clear()


@router.message(DonateStates.waiting_receipt)
async def receipt_not_photo(message: Message):
    await message.answer("📸 لطفاً عکس فیش رو ارسال کن، نه متن.")
