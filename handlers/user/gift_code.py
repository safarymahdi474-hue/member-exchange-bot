from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
from datetime import datetime
from config import DB_PATH
from utils.helpers import add_coins
from keyboards.user_kb import main_menu_kb, back_kb

router = Router()


class GiftCodeStates(StatesGroup):
    waiting_code = State()


@router.callback_query(F.data == "gift_code")
async def gift_code_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🎟️ کد هدیه\n\nکد هدیه خود را وارد کن:",
        reply_markup=back_kb()
    )
    await state.set_state(GiftCodeStates.waiting_code)
    await callback.answer()


@router.message(GiftCodeStates.waiting_code)
async def gift_code_use(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    user_id = message.from_user.id

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM gift_codes WHERE code = ?", (code,)) as cursor:
            gift = await cursor.fetchone()

        if not gift:
            await message.answer("❌ کد هدیه نامعتبر است.", reply_markup=main_menu_kb())
            await state.clear()
            return

        if not gift["is_active"]:
            await message.answer("❌ این کد هدیه غیرفعال شده.", reply_markup=main_menu_kb())
            await state.clear()
            return

        if gift["expires_at"] and datetime.now() > datetime.fromisoformat(gift["expires_at"]):
            await message.answer("❌ این کد هدیه منقضی شده.", reply_markup=main_menu_kb())
            await state.clear()
            return

        if gift["used_count"] >= gift["max_uses"]:
            await message.answer("❌ ظرفیت این کد هدیه تمام شده.", reply_markup=main_menu_kb())
            await state.clear()
            return

        async with db.execute(
            "SELECT 1 FROM gift_code_uses WHERE user_id = ? AND code_id = ?", (user_id, gift["id"])
        ) as cursor:
            already_used = await cursor.fetchone()

        if already_used:
            await message.answer("❌ قبلاً از این کد استفاده کردی.", reply_markup=main_menu_kb())
            await state.clear()
            return

        # اعمال کد
        await db.execute(
            "INSERT INTO gift_code_uses (user_id, code_id) VALUES (?, ?)", (user_id, gift["id"])
        )
        await db.execute(
            "UPDATE gift_codes SET used_count = used_count + 1 WHERE id = ?", (gift["id"],)
        )
        await db.commit()

    await add_coins(user_id, gift["coins"], "gift_code", f"کد هدیه: {code}")
    await message.answer(
        f"✅ کد هدیه اعمال شد!\n\n🪙 {gift['coins']} سکه به حسابت اضافه شد.",
        reply_markup=main_menu_kb()
    )
    await state.clear()
