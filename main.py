import os
import asyncio
from telegram import Bot
from scanner import get_new_tokens

async def main():
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    print("TOKEN EXISTS:", bool(token))
    print("CHAT_ID:", chat_id)

    if not token or not chat_id:
        print("MISSING ENV VARS — STOPPING")
        return

    bot = Bot(token=token)

    me = await bot.get_me()
    print(f"Bot connected: @{me.username}")

    # TEST MESSAGE (CRITICAL)
    try:
        await bot.send_message(chat_id=int(chat_id), text="🚀 TEST MESSAGE FROM WEB3RAY BOT")
        print("TEST MESSAGE SENT")
    except Exception as e:
        print("TEST FAILED:", e)

    while True:
        get_new_tokens(bot, chat_id)
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
