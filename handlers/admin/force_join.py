from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
from datetime import datetime, timedelta
from config import DB_PATH, ADMIN_IDS
from keyboards.admin_kb import back_admin_kb

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class ForceJoinStates(StatesGroup):
    waiting_channel_id = State()
    waiting_channel_name = State()
    waiting_remove_type = State()
    waiting_remove_value = State()


async def get_force_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM force_join_channels WHERE is_active = 1") as c:
            return await c.fetchall()


@router.callback_query(F.data == "admin_force_join")
async def force_join_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ دسترسی ندارید.", show_alert=True)

    channels = await get_force_channels()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for ch in channels:
        if ch["remove_type"] == "count":
            info = f"{ch['current_count']}/{ch['remove_value']} عضو"
        else:
            info = f"تا {str(ch['expires_at'])[:16]}"
        buttons.append([InlineKeyboardButton(
            text=f"❌ حذف | {ch['channel_name']} | {info}",
            callback_data=f"remove_force_{ch['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ افزودن کانال اجباری", callback_data="add_force_channel")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_admin")])

    await callback.message.answer(
        "🔒 کانال‌های عضویت اجباری:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.callback_query(F.data == "add_force_channel")
async def add_force_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("آیدی کانال رو وارد کن (مثال: @mychannel):")
    await state.set_state(ForceJoinStates.waiting_channel_id)
    await callback.answer()


@router.message(ForceJoinStates.waiting_channel_id)
async def add_force_name(message: Message, state: FSMContext):
    channel_id = message.text.strip()
    if not channel_id.startswith("@"):
        channel_id = "@" + channel_id
    await state.update_data(channel_id=channel_id)
    await message.answer("اسم نمایشی کانال رو وارد کن:")
    await state.set_state(ForceJoinStates.waiting_channel_name)


@router.message(ForceJoinStates.waiting_channel_name)
async def add_force_type(message: Message, state: FSMContext):
    await state.update_data(channel_name=message.text.strip())
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 بر اساس تعداد عضو", callback_data="force_type_count")],
        [InlineKeyboardButton(text="⏰ بر اساس زمان", callback_data="force_type_time")],
    ])
    await message.answer("نوع حذف عضویت اجباری رو انتخاب کن:", reply_markup=kb)
    await state.set_state(ForceJoinStates.waiting_remove_type)


@router.callback_query(F.data.startswith("force_type_"))
async def add_force_value(callback: CallbackQuery, state: FSMContext):
    remove_type = callback.data.replace("force_type_", "")
    await state.update_data(remove_type=remove_type)
    if remove_type == "count":
        await callback.message.answer("بعد از چند عضو شدن، کانال از لیست اجباری حذف بشه؟")
    else:
        await callback.message.answer("بعد از چند ساعت کانال از لیست اجباری حذف بشه؟")
    await state.set_state(ForceJoinStates.waiting_remove_value)
    await callback.answer()


@router.message(ForceJoinStates.waiting_remove_value)
async def add_force_confirm(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ عدد صحیح مثبت وارد کن.")
        return

    data = await state.get_data()
    expires_at = None
    if data["remove_type"] == "time":
        expires_at = (datetime.now() + timedelta(hours=value)).strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO force_join_channels (channel_id, channel_name, remove_type, remove_value, expires_at, is_active, current_count) "
            "VALUES (?, ?, ?, ?, ?, 1, 0) "
            "ON CONFLICT(channel_id) DO UPDATE SET "
            "channel_name=excluded.channel_name, "
            "remove_type=excluded.remove_type, "
            "remove_value=excluded.remove_value, "
            "expires_at=excluded.expires_at, "
            "is_active=1, "
            "current_count=0",
            (data["channel_id"], data["channel_name"], data["remove_type"], value, expires_at)
        )
        await db.commit()

    await message.answer(
        f"✅ کانال {data['channel_name']} به لیست عضویت اجباری اضافه شد!\n"
        f"نوع حذف: {'بعد از ' + str(value) + ' عضو' if data['remove_type'] == 'count' else 'بعد از ' + str(value) + ' ساعت'}"
    )
    await state.clear()


@router.callback_query(F.data.startswith("remove_force_"))
async def remove_force_channel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    ch_id = int(callback.data.split("_")[-1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE force_join_channels SET is_active = 0 WHERE id = ?", (ch_id,))
        await db.commit()
    await callback.answer("✅ کانال از لیست اجباری حذف شد.", show_alert=True)
    await force_join_panel(callback)
