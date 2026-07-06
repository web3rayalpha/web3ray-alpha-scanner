import os
import asyncio
from telegram import Bot

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
    print(f"✅ Bot connected successfully: @{me.username}")

    await bot.send_message(
        chat_id=int(chat_id),
        text="🚀 WEB3RAY Alpha Scanner is online!"
    )

    print("✅ Test message sent!")

if __name__ == "__main__":
    asyncio.run(main())
