from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
from config import DB_PATH, ADMIN_IDS
from keyboards.admin_kb import back_admin_kb

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class AddAdminStates(StatesGroup):
    waiting_user_id = State()
    waiting_permissions = State()


async def get_admins():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admins") as c:
            return await c.fetchall()


@router.callback_query(F.data == "admin_manage_admins")
async def manage_admins(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ دسترسی ندارید.", show_alert=True)

    admins = await get_admins()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for admin in admins:
        buttons.append([InlineKeyboardButton(
            text=f"❌ حذف | {admin['full_name']} | {admin['permissions']}",
            callback_data=f"remove_admin_{admin['user_id']}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ افزودن ادمین", callback_data="add_admin")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_admin")])

    await callback.message.answer(
        "👮 مدیریت ادمین‌ها:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.callback_query(F.data == "add_admin")
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("آیدی عددی تلگرام ادمین جدید رو وارد کن:")
    await state.set_state(AddAdminStates.waiting_user_id)
    await callback.answer()


@router.message(AddAdminStates.waiting_user_id)
async def add_admin_permissions(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ آیدی عددی وارد کن.")
        return

    await state.update_data(new_admin_id=user_id)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 دسترسی کامل", callback_data="perm_full")],
        [InlineKeyboardButton(text="📦 فقط سفارش‌ها", callback_data="perm_orders")],
        [InlineKeyboardButton(text="📢 فقط کانال‌ها", callback_data="perm_channels")],
        [InlineKeyboardButton(text="📣 فقط پیام همگانی", callback_data="perm_broadcast")],
    ])
    await message.answer("سطح دسترسی ادمین جدید رو انتخاب کن:", reply_markup=kb)
    await state.set_state(AddAdminStates.waiting_permissions)


@router.callback_query(F.data.startswith("perm_"))
async def add_admin_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    data = await state.get_data()
    new_admin_id = data["new_admin_id"]
    permission = callback.data.replace("perm_", "")

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT full_name FROM users WHERE user_id = ?", (new_admin_id,)) as c:
            user = await c.fetchone()
        full_name = user[0] if user else str(new_admin_id)
        await db.execute(
            "INSERT OR REPLACE INTO admins (user_id, full_name, permissions) VALUES (?, ?, ?)",
            (new_admin_id, full_name, permission)
        )
        await db.commit()

    ADMIN_IDS.append(new_admin_id)
    await callback.message.answer(f"✅ ادمین {full_name} با دسترسی {permission} اضافه شد.")
    try:
        await callback.bot.send_message(new_admin_id, "🎉 شما به عنوان ادمین ربات اضافه شدید!")
    except Exception:
        pass
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("remove_admin_"))
async def remove_admin(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split("_")[-1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()
    if user_id in ADMIN_IDS:
        ADMIN_IDS.remove(user_id)
    await callback.answer("✅ ادمین حذف شد.", show_alert=True)
    await manage_admins(callback)
