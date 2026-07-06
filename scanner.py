import requests
import os
from telegram import Bot

def get_new_tokens(bot: Bot, chat_id: int):
    print("🔍 Starting scan safely...")

    url = "https://api.dexscreener.com/latest/dex/search?q=solana"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()

        pairs = data.get("pairs", [])

        print(f"TOTAL PAIRS FOUND: {len(pairs)}")

        sent = False

        for pair in pairs[:10]:
            base = pair.get("baseToken", {})
            symbol = base.get("symbol")
            price = pair.get("priceUsd")

            print(f"{symbol} | ${price}")

            if symbol and symbol != "SOL" and not sent:
                message = f"🚨 WEB3RAY ALERT\n\nToken: {symbol}\nPrice: ${price}"

                bot.send_message(chat_id=chat_id, text=message)
                sent = True

        print("SCAN COMPLETE")

    except Exception as e:
        print("SCAN ERROR:", str(e))
