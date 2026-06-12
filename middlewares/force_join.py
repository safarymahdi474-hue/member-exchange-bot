from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite
from config import DB_PATH
from typing import Callable, Dict, Any, Awaitable


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
            if member.status not in ("member", "administrator", "creator"):
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


class ForceJoinMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        bot = data["bot"]
        user_id = event.from_user.id

        # callback های مربوط به force join رو رد کن
        if isinstance(event, CallbackQuery):
            if event.data == "recheck_force_join":
                return await handler(event, data)

        unjoin = await get_unjoin_channel(bot, user_id)
        if unjoin:
            kb = make_force_join_kb(unjoin)
            if isinstance(event, Message):
                await event.answer(
                    f"⚠️ برای استفاده از ربات باید در کانال ما عضو بشی:",
                    reply_markup=kb
                )
            elif isinstance(event, CallbackQuery):
                await event.message.answer(
                    f"⚠️ برای استفاده از ربات باید در کانال ما عضو بشی:",
                    reply_markup=kb
                )
                await event.answer()
            return
        return await handler(event, data)
