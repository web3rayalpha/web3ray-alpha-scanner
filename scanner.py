import requests
import os
from telegram import Bot

def get_new_tokens():
    print("🔍 RUNNING ALPHA SIGNAL SCANNER")

    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    bot = Bot(token=token) if token and chat_id else None

    url = "https://api.dexscreener.com/latest/dex/search?q=raydium"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()

        pairs = data.get("pairs", [])

        print("TOTAL PAIRS FOUND:", len(pairs))

        sent = 0

        for pair in pairs:
            base = pair.get("baseToken", {})
            symbol = base.get("symbol")
            price = pair.get("priceUsd")
            liquidity = pair.get("liquidity", {}).get("usd", 0)

            if not symbol or symbol == "SOL":
                continue

            # simple alpha filter
            if liquidity < 200000:
                continue

            msg = f"🚨 WEB3RAY SIGNAL\n\nToken: {symbol}\nPrice: ${price}\nLiquidity: ${liquidity}"

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
