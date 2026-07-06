import requests
import os
from telegram import Bot

def get_new_tokens():
    print("🔍 Scanning Solana alpha opportunities...")

    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    bot = Bot(token=token) if token and chat_id else None

    url = "https://api.dexscreener.com/latest/dex/search?q=solana"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()

        pairs = data.get("pairs", [])

        print(f"TOTAL PAIRS FOUND: {len(pairs)}")

        sent = 0

        for pair in pairs[:20]:  # LIMIT FIRST
            base = pair.get("baseToken", {})
            symbol = base.get("symbol")
            price = pair.get("priceUsd")

            if not symbol:
                continue

            if symbol in ["SOL", "USDC", "USDT"]:
                continue

            msg = f"🚨 TOKEN FOUND\n\nToken: {symbol}\nPrice: ${price}"

            print(msg)

            if bot:
                try:
                    bot.send_message(chat_id=int(chat_id), text=msg)
                except Exception as e:
                    print("Telegram error:", e)

            sent += 1
            if sent >= 5:
                break

        print("SCAN COMPLETE")

    except Exception as e:
        print("ERROR:", str(e))
