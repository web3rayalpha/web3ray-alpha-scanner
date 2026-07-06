import requests
import os
from telegram import Bot
import asyncio

def get_new_tokens():
    print("🔍 Starting scan safely...")

    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    url = "https://api.dexscreener.com/latest/dex/search?q=solana"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()

        pairs = data.get("pairs", [])

        print(f"TOTAL PAIRS FOUND: {len(pairs)}")

        for pair in pairs[:5]:
            base = pair.get("baseToken", {})
            symbol = base.get("symbol")
            price = pair.get("priceUsd")

            print(f"{symbol} | ${price}")

            # send ONE test alert
            if token and chat_id and symbol and symbol != "SOL":
                message = f"🚨 WEB3RAY ALERT\n\nToken: {symbol}\nPrice: ${price}"

                try:
                    bot = Bot(token=token)
                    asyncio.run(bot.send_message(chat_id=int(chat_id), text=message))
                except Exception as e:
                    print("Telegram error:", e)

        print("SCAN COMPLETE")

    except Exception as e:
        print("SCAN ERROR:", str(e))
