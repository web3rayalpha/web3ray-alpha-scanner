import os
import asyncio
from telegram import Bot
from scanner import get_new_tokens

async def main():
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    bot = Bot(token=token) if token and chat_id else None

    if bot:
        me = await bot.get_me()
        print(f"Bot connected: @{me.username}")

    while True:
        get_new_tokens()

        print("WAITING 30s BEFORE NEXT SCAN...\n")
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
