from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.helpers import get_user, deduct_coins, add_coins
from keyboards.user_kb import main_menu_kb, back_kb

router = Router()


class TransferStates(StatesGroup):
    waiting_receiver = State()
    waiting_amount = State()


@router.message(F.text == "💸 انتقال سکه")
async def transfer_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    await message.answer(
        f"💸 انتقال سکه\n\n"
        f"🪙 موجودی شما: {user['coins']} سکه\n\n"
        f"آیدی عددی تلگرام گیرنده رو وارد کن:",
        reply_markup=back_kb()
    )
    await state.set_state(TransferStates.waiting_receiver)


@router.message(TransferStates.waiting_receiver)
async def transfer_receiver(message: Message, state: FSMContext):
    try:
        receiver_id = int(message.text.strip())
        if receiver_id == message.from_user.id:
            await message.answer("❌ نمی‌تونی به خودت سکه بفرستی!")
            return
    except ValueError:
        await message.answer("⚠️ آیدی عددی تلگرام وارد کن.")
        return

    receiver = await get_user(receiver_id)
    if not receiver:
        await message.answer("❌ این کاربر در ربات ثبت‌نام نکرده.")
        return

    await state.update_data(receiver_id=receiver_id, receiver_name=receiver["full_name"])
    user = await get_user(message.from_user.id)
    await message.answer(
        f"✅ گیرنده: {receiver['full_name']}\n\n"
        f"🪙 موجودی شما: {user['coins']} سکه\n\n"
        f"چند سکه میخوای بفرستی؟",
        reply_markup=back_kb()
    )
    await state.set_state(TransferStates.waiting_amount)


@router.message(TransferStates.waiting_amount)
async def transfer_amount(message: Message, state: FSMContext, bot):
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ عدد صحیح مثبت وارد کن.")
        return

    data = await state.get_data()
    receiver_id = data["receiver_id"]
    receiver_name = data["receiver_name"]
    sender = await get_user(message.from_user.id)

    if sender["coins"] < amount:
        await message.answer(f"❌ سکه کافی نداری! موجودی: {sender['coins']} سکه")
        await state.clear()
        return

    success = await deduct_coins(
        message.from_user.id, amount, "transfer_out",
        f"انتقال به {receiver_name} ({receiver_id})"
    )
    if success:
        await add_coins(
            receiver_id, amount, "transfer_in",
            f"دریافت از {sender['full_name']} ({message.from_user.id})"
        )
        await message.answer(
            f"✅ {amount} سکه با موفقیت ارسال شد!\n"
            f"👤 گیرنده: {receiver_name}",
            reply_markup=main_menu_kb()
        )
        try:
            await bot.send_message(
                receiver_id,
                f"💸 {amount} سکه از طرف {sender['full_name']} دریافت کردی! 🎉"
            )
        except Exception:
            pass

    await state.clear()
