from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
from config import DB_PATH, ADMIN_IDS
from keyboards.admin_kb import admin_gift_codes_kb, back_admin_kb

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.callback_query(F.data == "admin_gift_codes")
async def admin_gift_codes(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ دسترسی ندارید.", show_alert=True)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM gift_codes ORDER BY created_at DESC") as c:
            codes = await c.fetchall()

    await callback.message.answer(
        "🎟️ مدیریت کدهای هدیه:",
        reply_markup=admin_gift_codes_kb([dict(c) for c in codes])
    )
    await callback.answer()


class CreateGiftCodeStates(StatesGroup):
    waiting_code = State()
    waiting_coins = State()
    waiting_max_uses = State()
    waiting_expires = State()


@router.callback_query(F.data == "create_gift_code")
async def create_gift_code_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer(
        "➕ ساخت کد هدیه جدید\n\n"
        "متن کد را وارد کن (مثال: GIFT2024):\n"
        "حروف بزرگ انگلیسی توصیه میشه"
    )
    await state.set_state(CreateGiftCodeStates.waiting_code)
    await callback.answer()


@router.message(CreateGiftCodeStates.waiting_code)
async def create_gift_code_coins(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM gift_codes WHERE code = ?", (code,)) as c:
            if await c.fetchone():
                await message.answer("❌ این کد قبلاً استفاده شده. کد دیگری وارد کن:")
                return
    await state.update_data(code=code)
    await message.answer(f"✅ کد: {code}\n\nتعداد سکه این کد را وارد کن:")
    await state.set_state(CreateGiftCodeStates.waiting_coins)


@router.message(CreateGiftCodeStates.waiting_coins)
async def create_gift_code_max_uses(message: Message, state: FSMContext):
    try:
        coins = int(message.text.strip())
        if coins <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ عدد صحیح مثبت وارد کن.")
        return
    await state.update_data(coins=coins)
    await message.answer(f"🪙 سکه: {coins}\n\nحداکثر تعداد استفاده را وارد کن:")
    await state.set_state(CreateGiftCodeStates.waiting_max_uses)


@router.message(CreateGiftCodeStates.waiting_max_uses)
async def create_gift_code_expires(message: Message, state: FSMContext):
    try:
        max_uses = int(message.text.strip())
        if max_uses <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ عدد صحیح مثبت وارد کن.")
        return
    await state.update_data(max_uses=max_uses)
    await message.answer(
        f"🔢 حداکثر استفاده: {max_uses}\n\n"
        f"تاریخ انقضا را وارد کن (فرمت: 2024-12-31)\n"
        f"یا بنویس - برای بدون انقضا:"
    )
    await state.set_state(CreateGiftCodeStates.waiting_expires)


@router.message(CreateGiftCodeStates.waiting_expires)
async def create_gift_code_finish(message: Message, state: FSMContext):
    expires = message.text.strip()
    expires_at = None
    if expires != "-":
        try:
            from datetime import datetime
            datetime.strptime(expires, "%Y-%m-%d")
            expires_at = expires
        except ValueError:
            await message.answer("⚠️ فرمت تاریخ اشتباه است. (مثال: 2024-12-31)")
            return

    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO gift_codes (code, coins, max_uses, expires_at) VALUES (?, ?, ?, ?)",
            (data["code"], data["coins"], data["max_uses"], expires_at)
        )
        await db.commit()

    await message.answer(
        f"✅ کد هدیه ساخته شد!\n\n"
        f"🎟️ کد: {data['code']}\n"
        f"🪙 سکه: {data['coins']}\n"
        f"🔢 حداکثر استفاده: {data['max_uses']}\n"
        f"📅 انقضا: {expires_at or 'ندارد'}"
    )
    await state.clear()


@router.callback_query(F.data.startswith("toggle_code_"))
async def toggle_gift_code(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    code_id = int(callback.data.split("_")[-1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE gift_codes SET is_active = 1 - is_active WHERE id = ?", (code_id,))
        await db.commit()
    await callback.answer("✅ وضعیت کد تغییر کرد.", show_alert=True)
    await admin_gift_codes(callback)
    @router.callback_query(F.data.startswith("delete_code_"))
async def delete_gift_code(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    code_id = int(callback.data.split("_")[-1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM gift_codes WHERE id = ?", (code_id,))
        await db.execute("DELETE FROM gift_code_uses WHERE code_id = ?", (code_id,))
        await db.commit()
    await callback.answer("✅ کد هدیه حذف شد.", show_alert=True)
    await admin_gift_codes(callback)
