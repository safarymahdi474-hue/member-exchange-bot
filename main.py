import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database.db import init_db

from handlers.user import start, profile, tasks, orders, transfer, gift_code
from handlers.admin import panel, gift_codes, broadcast

logging.basicConfig(level=logging.INFO)


async def main():
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # ثبت روترها
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(tasks.router)
    dp.include_router(orders.router)
    dp.include_router(transfer.router)
    dp.include_router(gift_code.router)
    dp.include_router(panel.router)
    dp.include_router(gift_codes.router)
    dp.include_router(broadcast.router)

    print("✅ ربات استارت شد!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
