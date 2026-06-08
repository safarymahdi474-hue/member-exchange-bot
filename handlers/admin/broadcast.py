from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS
from utils.helpers import get_all_user_ids
from keyboards.admin_kb import back_admin_kb

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class BroadcastStates(StatesGroup):
    waiting_message = State()


@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ دسترسی ندارید.", show_alert=True)

    user_ids = await get_all_user_ids()
    await callback.message.answer(
        f"📣 پیام همگانی\n\n"
        f"👥 تعداد کاربران: {len(user_ids)} نفر\n\n"
        f"متن پیام را بنویس:",
        reply_markup=back_admin_kb()
    )
    await state.set_state(BroadcastStates.waiting_message)
    await callback.answer()


@router.message(BroadcastStates.waiting_message)
async def broadcast_send(message: Message, state: FSMContext, bot):
    if not is_admin(message.from_user.id):
        return

    user_ids = await get_all_user_ids()
    sent = 0
    failed = 0

    status_msg = await message.answer(f"⏳ در حال ارسال به {len(user_ids)} کاربر...")

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, f"📣 پیام مدیریت:\n\n{message.text}")
            sent += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ پیام همگانی ارسال شد!\n\n"
        f"✔️ موفق: {sent} نفر\n"
        f"❌ ناموفق: {failed} نفر"
    )
    await state.clear()
