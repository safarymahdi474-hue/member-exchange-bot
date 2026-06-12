from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎁 عضو شو و سکه بگیر")],
            [KeyboardButton(text="📦 سفارش ممبر"), KeyboardButton(text="💸 انتقال سکه")],
            [KeyboardButton(text="👤 پروفایل")],
        ],
        resize_keyboard=True
    )


def profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 تاریخچه سکه‌ها", callback_data="history")],
        [InlineKeyboardButton(text="🎟️ کد هدیه", callback_data="gift_code")],
        [InlineKeyboardButton(text="💰 خرید سکه", callback_data="buy_coins")],
        [InlineKeyboardButton(text="📢 درخواست تبلیغ", callback_data="advertise")],
    ])


def channels_kb(channels: list, joined_ids: list):
    buttons = []
    for ch in channels:
        status = "✅" if ch["channel_id"] in joined_ids else "➕"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {ch['channel_name']}",
            url=f"https://t.me/{ch['channel_id'].lstrip('@')}"
        )])
    buttons.append([InlineKeyboardButton(text="✔️ تأیید عضویت‌ها", callback_data="verify_joins")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_main")]
    ])
