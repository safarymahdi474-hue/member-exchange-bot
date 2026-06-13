from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
import aiosqlite
from config import DB_PATH, ADMIN_IDS
from typing import Callable, Dict, Any


async def get_unjoin_channel(bot, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE force_join_channels SET is_active = 0 "
            "WHERE remove_type = 'time' AND expires_at < datetime('now')"
        )
        await db.commit()
        async with db.execute(
            "SELECT * FROM force_join_channels WHERE is_active = 1"
        ) as c:
            channels = await c.fetchall()

    for ch in channels:
        try:
            member = await bot.get_chat_member(ch["channel_id"], user_id)
            if member.status in ("left", "kicked", "restricted"):
                return ch
        except Exception:
            pass
    return None


def make_force_join_kb(channel):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"➕ عضو شو در {channel['channel_name']}",
            url=f"https://t.me/{channel['channel_id'].lstrip('@')}"
        )],
        [InlineKeyboardButton(
            text="✔️ عضو شدم",
            callback_data="recheck_force_join"
        )]
    ])


# callback هایی که باید بدون چک رد بشن
ALLOWED_CALLBACKS = (
    "recheck_force_join",
    "force_type_count",
    "force_type_time",
    "add_force_channel",
    "admin_force_join",
    "remove_force_",
    "back_admin",
)


class ForceJoinMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable,
        event,
        data: Dict[str, Any]
    ) -> Any:
        bot = data["bot"]

        if isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            # ادمین رو رد کن
            if user_id in ADMIN_IDS:
                return await handler(event, data)
            # callback های مجاز رو رد کن
            if event.data and any(event.data.startswith(cb) for cb in ALLOWED_CALLBACKS):
                return await handler(event, data)

        elif isinstance(event, Message):
            user_id = event.from_user.id
            # ادمین رو رد کن
            if user_id in ADMIN_IDS:
                return await handler(event, data)
        else:
            return await handler(event, data)

        unjoin = await get_unjoin_channel(bot, user_id)
        if unjoin:
            kb = make_force_join_kb(unjoin)
            text = "⚠️ برای استفاده از ربات باید در کانال ما عضو بشی:"
            try:
                if isinstance(event, Message):
                    await event.answer(text, reply_markup=kb)
                elif isinstance(event, CallbackQuery):
                    await event.message.answer(text, reply_markup=kb)
                    await event.answer()
            except TelegramBadRequest:
                pass
            return

        return await handler(event, data)
