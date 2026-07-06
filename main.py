import os
from telegram import Bot
import asyncio

async def main():
    token = os.getenv("BOT_TOKEN")

    if not token:
        print("BOT_TOKEN not found!")
        return

    bot = Bot(token=token)

    me = await bot.get_me()
    print(f"✅ Bot connected successfully: @{me.username}")

if __name__ == "__main__":
    asyncio.run(main())
