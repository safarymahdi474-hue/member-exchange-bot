from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
from config import DB_PATH, ADMIN_IDS
from database.db import get_setting, set_setting
from utils.helpers import get_user, get_referral_count, add_coins
from keyboards.admin_kb import (
    admin_profile_kb, admin_orders_kb, admin_channels_kb,
    admin_gift_codes_kb, admin_settings_kb, back_admin_kb
)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ── آمار کلی ──────────────────────────────────────────────
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ دسترسی ندارید.", show_alert=True)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            user_count = (await c.fetchone())[0]
        async with db.execute("SELECT SUM(coins) FROM users") as c:
            total_coins = (await c.fetchone())[0] or 0
        async with db.execute("SELECT COUNT(*) FROM orders WHERE status='active'") as c:
            active_orders = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM channels WHERE is_active=1") as c:
            active_channels = (await c.fetchone())[0]

    await callback.message.answer(
        f"📈 آمار کلی ربات\n\n"
        f"👥 کاربران: {user_count} نفر\n"
        f"🪙 سکه در گردش: {total_coins}\n"
        f"📦 سفارش‌های فعال: {active_orders}\n"
        f"📢 کانال‌های فعال: {active_channels}",
        reply_markup=back_admin_kb()
    )
    await callback.answer()


# ── مدیریت سفارش‌ها ───────────────────────────────────────
@router.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ دسترسی ندارید.", show_alert=True)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE status='active' ORDER BY created_at DESC LIMIT 30"
        ) as c:
            orders = await c.fetchall()

    if not orders:
        await callback.answer("📦 سفارش فعالی وجود ندارد.", show_alert=True)
        return

    await callback.message.answer(
        f"📦 سفارش‌های فعال ({len(orders)} مورد):",
        reply_markup=admin_orders_kb([dict(o) for o in orders])
    )
    await callback.answer()


class CancelOrderStates(StatesGroup):
    waiting_reason = State()


@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ دسترسی ندارید.", show_alert=True)

    order_id = int(callback.data.split("_")[-1])
    await state.update_data(order_id=order_id)
    await callback.message.answer(
        "📝 دلیل لغو سفارش را بنویس:\n(یا بنویس - برای بدون دلیل)",
        reply_markup=back_admin_kb()
    )
    await state.set_state(CancelOrderStates.waiting_reason)
    await callback.answer()


@router.message(CancelOrderStates.waiting_reason)
async def cancel_order_confirm(message: Message, state: FSMContext, bot):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    order_id = data["order_id"]
    reason = message.text.strip()
    if reason == "-":
        reason = "دلیلی ذکر نشده"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as c:
            order = await c.fetchone()

        if not order or order["status"] != "active":
            await message.answer("❌ سفارش یافت نشد یا قبلاً لغو شده.")
            await state.clear()
            return

        await db.execute(
            "UPDATE orders SET status='cancelled', cancel_reason=? WHERE id=?",
            (reason, order_id)
        )
        await db.commit()

    await add_coins(order["user_id"], order["coins_spent"], "admin", f"برگشت سکه - لغو سفارش #{order_id}")

    await message.answer(f"✅ سفارش #{order_id} لغو شد و {order['coins_spent']} سکه برگشت داده شد.")

    try:
        await bot.send_message(
            order["user_id"],
            f"❌ سفارش شما لغو شد\n\n"
            f"📢 کانال: {order['channel_name']}\n"
            f"💬 دلیل: {reason}\n\n"
            f"🪙 {order['coins_spent']} سکه به حسابتون برگشت"
        )
    except Exception:
        pass

    await state.clear()


# ── مدیریت کانال‌ها ───────────────────────────────────────
@router.callback_query(F.data == "admin_channels")
async def admin_channels(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ دسترسی ندارید.", show_alert=True)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM channels ORDER BY added_at DESC") as c:
            channels = await c.fetchall()

    await callback.message.answer(
        "📢 مدیریت کانال‌ها:",
        reply_markup=admin_channels_kb([dict(ch) for ch in channels])
    )
    await callback.answer()


class AddChannelStates(StatesGroup):
    waiting_channel_id = State()
    waiting_channel_name = State()


@router.callback_query(F.data == "add_channel")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer("آیدی کانال رو وارد کن (مثال: @mychannel):")
    await state.set_state(AddChannelStates.waiting_channel_id)
    await callback.answer()


@router.message(AddChannelStates.waiting_channel_id)
async def add_channel_id(message: Message, state: FSMContext):
    channel_id = message.text.strip()
    if not channel_id.startswith("@"):
        channel_id = "@" + channel_id
    await state.update_data(channel_id=channel_id)
    await message.answer("اسم نمایشی کانال رو وارد کن:")
    await state.set_state(AddChannelStates.waiting_channel_name)


@router.message(AddChannelStates.waiting_channel_name)
async def add_channel_name(message: Message, state: FSMContext):
    data = await state.get_data()
    channel_id = data["channel_id"]
    channel_name = message.text.strip()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO channels (channel_id, channel_name) VALUES (?, ?)",
            (channel_id, channel_name)
        )
        await db.commit()

    await message.answer(f"✅ کانال {channel_name} ({channel_id}) اضافه شد.")
    await state.clear()


@router.callback_query(F.data.startswith("toggle_channel_"))
async def toggle_channel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    ch_id = int(callback.data.split("_")[-1])
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE channels SET is_active = 1 - is_active WHERE id = ?", (ch_id,))
        await db.commit()
    await callback.answer("✅ وضعیت کانال تغییر کرد.", show_alert=True)
    await admin_channels(callback)


# ── تنظیمات ────────────────────────────────────────────────
@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ دسترسی ندارید.", show_alert=True)

    s1 = await get_setting("coins_start")
    s2 = await get_setting("coins_per_join")
    s3 = await get_setting("coins_per_member")
    s4 = await get_setting("coins_per_referral")

    await callback.message.answer(
        f"⚙️ تنظیمات فعلی:\n\n"
        f"🎁 سکه شروع: {s1}\n"
        f"✅ سکه هر عضویت: {s2}\n"
        f"📦 هزینه هر ممبر: {s3}\n"
        f"👥 سکه رفرال: {s4}\n\n"
        f"برای تغییر روی گزینه مورد نظر بزن:",
        reply_markup=admin_settings_kb()
    )
    await callback.answer()


class SettingsStates(StatesGroup):
    waiting_value = State()


SETTINGS_MAP = {
    "set_coins_start": ("coins_start", "🎁 سکه شروع"),
    "set_coins_per_join": ("coins_per_join", "✅ سکه هر عضویت"),
    "set_coins_per_member": ("coins_per_member", "📦 هزینه هر ممبر"),
    "set_coins_per_referral": ("coins_per_referral", "👥 سکه رفرال"),
}


@router.callback_query(F.data.in_(SETTINGS_MAP.keys()))
async def setting_change_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    key, label = SETTINGS_MAP[callback.data]
    current = await get_setting(key)
    await state.update_data(setting_key=key, setting_label=label)
    await callback.message.answer(
        f"⚙️ {label}\nمقدار فعلی: {current}\n\nمقدار جدید را وارد کن:"
    )
    await state.set_state(SettingsStates.waiting_value)
    await callback.answer()


@router.message(SettingsStates.waiting_value)
async def setting_change_confirm(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        value = int(message.text.strip())
        if value < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ عدد صحیح غیر منفی وارد کن.")
        return

    data = await state.get_data()
    await set_setting(data["setting_key"], value)
    await message.answer(f"✅ {data['setting_label']} به {value} تغییر یافت.")
    await state.clear()


# ── بازگشت به پنل ادمین ────────────────────────────────────
@router.callback_query(F.data == "back_admin")
async def back_admin(callback: CallbackQuery):
    from handlers.user.profile import show_profile
    await show_profile(callback.message)
    await callback.answer()
