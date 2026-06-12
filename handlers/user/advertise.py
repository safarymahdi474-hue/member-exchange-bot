from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS
from keyboards.user_kb import main_menu_kb, back_kb

router = Router()


class AdvertiseStates(StatesGroup):
    waiting_message = State()


@router.callback_query(F.data == "advertise")
async def advertise_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📢 درخواست تبلیغ\n\n"
        "پیام خودت رو بنویس (میتونی عکس، متن یا لینک بفرستی):",
        reply_markup=back_kb()
    )
    await state.set_state(AdvertiseStates.waiting_message)
    await callback.answer()


@router.message(AdvertiseStates.waiting_message)
async def advertise_send(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    full_name = message.from_user.full_name or ""
    username = message.from_user.username or "ندارد"

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📢 درخواست تبلیغ\n\n"
                f"👤 نام: {full_name}\n"
                f"🆔 آیدی: {user_id}\n"
                f"👤 یوزرنیم: @{username}\n\n"
                f"پیام تبلیغاتی:"
            )
            await message.forward(admin_id)
        except Exception:
            pass

    await message.answer(
        "✅ درخواست تبلیغ شما ارسال شد!\n"
        "ادمین به زودی با شما تماس میگیره.",
        reply_markup=main_menu_kb()
    )
    await state.clear()
