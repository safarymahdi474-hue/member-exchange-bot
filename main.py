import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database.db import init_db, migrate_db
from handlers.user import start, profile, tasks, orders, transfer, gift_code, donate, advertise, recheck
from handlers.admin import panel, gift_codes, broadcast, admins, force_join
from handlers.user import leaderboard as user_leaderboard
from handlers.admin import leaderboard as admin_leaderboard
from middlewares.force_join import ForceJoinMiddleware

logging.basicConfig(level=logging.INFO)


async def main():
    await init_db()
    await migrate_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(ForceJoinMiddleware())
    dp.callback_query.middleware(ForceJoinMiddleware())

    dp.include_router(recheck.router)
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(tasks.router)
    dp.include_router(orders.router)
    dp.include_router(transfer.router)
    dp.include_router(gift_code.router)
    dp.include_router(donate.router)
    dp.include_router(advertise.router)
    dp.include_router(panel.router)
    dp.include_router(gift_codes.router)
    dp.include_router(broadcast.router)
    dp.include_router(admins.router)
    dp.include_router(force_join.router)
    dp.include_router(user_leaderboard.router)
    dp.include_router(admin_leaderboard.router)

    print("✅ ربات استارت شد!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
