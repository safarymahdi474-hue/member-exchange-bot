from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
import aiosqlite
from config import DB_PATH

router = Router()


async def get_unjoin_channel(bot, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
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


@router.callback_query(F.data == "recheck_force_join")
async def recheck_force_join(callback: CallbackQuery, bot: Bot):
    unjoin = await get_unjoin_channel(bot, callback.from_user.id)
    if unjoin:
        await callback.answer("❌ هنوز عضو نشدی!", show_alert=True)
        return

    await callback.message.delete()
    await callback.answer("✅ عضو شدی! حالا میتونی از ربات استفاده کنی.", show_alert=True)
    from keyboards.user_kb import main_menu_kb
    await callback.message.answer("👋 خوش اومدی! از منو پایین شروع کن 👇", reply_markup=main_menu_kb())
