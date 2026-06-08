from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
from config import DB_PATH
from database.db import get_setting
from utils.helpers import get_user, deduct_coins
from keyboards.user_kb import main_menu_kb, back_kb

router = Router()


class OrderStates(StatesGroup):
    waiting_channel = State()
    waiting_quantity = State()


@router.message(F.text == "📦 سفارش ممبر")
async def order_start(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    coins_per_member = await get_setting("coins_per_member")
    await message.answer(
        f"📦 سفارش ممبر\n\n"
        f"🪙 موجودی شما: {user['coins']} سکه\n"
        f"💰 هزینه هر ممبر: {coins_per_member} سکه\n\n"
        f"آیدی یا لینک کانال مورد نظر رو ارسال کن:\n"
        f"مثال: @mychannel",
        reply_markup=back_kb()
    )
    await state.set_state(OrderStates.waiting_channel)


@router.message(OrderStates.waiting_channel)
async def order_channel(message: Message, state: FSMContext):
    channel = message.text.strip()
    if not channel.startswith("@"):
        channel = "@" + channel
    await state.update_data(channel=channel)
    user = await get_user(message.from_user.id)
    coins_per_member = await get_setting("coins_per_member")
    max_members = user["coins"] // coins_per_member
    await message.answer(
        f"✅ کانال: {channel}\n\n"
        f"🪙 موجودی شما: {user['coins']} سکه\n"
        f"📊 حداکثر {max_members} ممبر می‌تونی سفارش بدی\n\n"
        f"تعداد ممبر مورد نظر رو بنویس:",
        reply_markup=back_kb()
    )
    await state.set_state(OrderStates.waiting_quantity)


@router.message(OrderStates.waiting_quantity)
async def order_quantity(message: Message, state: FSMContext):
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ عدد صحیح وارد کن.")
        return

    data = await state.get_data()
    channel = data["channel"]
    coins_per_member = await get_setting("coins_per_member")
    total_cost = quantity * coins_per_member
    user = await get_user(message.from_user.id)

    if user["coins"] < total_cost:
        await message.answer(
            f"❌ سکه کافی نداری!\n"
            f"🪙 موجودی: {user['coins']} سکه\n"
            f"💰 نیاز داری: {total_cost} سکه"
        )
        await state.clear()
        return

    success = await deduct_coins(message.from_user.id, total_cost, "order", f"سفارش {quantity} ممبر برای {channel}")
    if success:
        async with aiosqlite.connect(DB_PATH) as db:
            # ثبت سفارش
            await db.execute(
                "INSERT INTO orders (user_id, channel_id, channel_name, quantity, coins_spent) VALUES (?, ?, ?, ?, ?)",
                (message.from_user.id, channel, channel, quantity, total_cost)
            )
            # اضافه کردن خودکار کانال به لیست
            await db.execute(
                "INSERT OR IGNORE INTO channels (channel_id, channel_name, is_active) VALUES (?, ?, 1)",
                (channel, channel)
            )
            await db.commit()

        await message.answer(
            f"✅ سفارش ثبت شد!\n\n"
            f"📢 کانال: {channel}\n"
            f"👥 تعداد: {quantity} ممبر\n"
            f"🪙 هزینه: {total_cost} سکه کسر شد\n\n"
            f"کانال شما به لیست عضویت اضافه شد ✅",
            reply_markup=main_menu_kb()
        )
    await state.clear()


@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("🏠 منوی اصلی", reply_markup=main_menu_kb())
    await callback.answer()
