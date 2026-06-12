from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 تاریخچه سکه‌ها", callback_data="history")],
        [InlineKeyboardButton(text="🎟️ کد هدیه", callback_data="gift_code")],
        [InlineKeyboardButton(text="📈 آمار کلی ربات", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📦 مدیریت سفارش‌ها", callback_data="admin_orders")],
        [InlineKeyboardButton(text="📢 مدیریت کانال‌ها", callback_data="admin_channels")],
        [InlineKeyboardButton(text="🎟️ مدیریت کدهای هدیه", callback_data="admin_gift_codes")],
        [InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="admin_settings")],
        [InlineKeyboardButton(text="📣 پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📦 حداقل سفارش ممبر", callback_data="set_min_order")],
        [InlineKeyboardButton(text="👮 مدیریت ادمین‌ها", callback_data="admin_manage_admins")],
        [InlineKeyboardButton(text="🔒 کانال عضویت اجباری", callback_data="admin_force_join")],
    ])


def admin_orders_kb(orders: list):
    buttons = []
    for order in orders:
        buttons.append([InlineKeyboardButton(
            text=f"❌ لغو | {order['channel_name']} | {order['quantity']} ممبر",
            callback_data=f"cancel_order_{order['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_channels_kb(channels: list):
    buttons = []
    for ch in channels:
        status = "✅" if ch["is_active"] else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {ch['channel_name']}",
            callback_data=f"toggle_channel_{ch['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ افزودن کانال", callback_data="add_channel")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_gift_codes_kb(codes: list):
    buttons = []
    for code in codes:
        buttons.append([
            InlineKeyboardButton(
                text=f"{'✅' if code['is_active'] else '❌'} {code['code']} | {code['coins']}🪙 | {code['used_count']}/{code['max_uses']}",
                callback_data=f"toggle_code_{code['id']}"
            ),
            InlineKeyboardButton(
                text="🗑️",
                callback_data=f"delete_code_{code['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="➕ ساخت کد جدید", callback_data="create_gift_code")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_settings_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 سکه شروع", callback_data="set_coins_start")],
        [InlineKeyboardButton(text="✅ سکه هر عضویت", callback_data="set_coins_per_join")],
        [InlineKeyboardButton(text="📦 هزینه هر ممبر", callback_data="set_coins_per_member")],
        [InlineKeyboardButton(text="👥 سکه رفرال", callback_data="set_coins_per_referral")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_admin")],
    ])


def back_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_admin")]
    ])
