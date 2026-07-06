 import os
import asyncio
from telegram import Bot
from scanner import get_new_tokens

async def main():
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    if not token:
        print("BOT_TOKEN not found!")
        return

    if not chat_id:
        print("CHAT_ID not found!")
        return

    bot = Bot(token=token)

    me = await bot.get_me()
    print(f"Bot connected: @{me.username}")

    # SAFE CALL (no crash risk)
    get_new_tokens()

    print("WEB3RAY Alpha Scanner running safely.")

if __name__ == "__main__":
    asyncio.run(main())
