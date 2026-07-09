import requests
import time

seen_tokens = set()

URL = "https://api.dexscreener.com/latest/dex/search?q=raydium"


def get_new_tokens(token, chat_id):
    print("🔍 WEB3RAY V2 SCANNING")

    try:
        response = requests.get(URL, timeout=10)
        data = response.json()

        pairs = data.get("pairs", [])

        sent = 0

        for pair in pairs:

            base = pair.get("baseToken", {})

            symbol = base.get("symbol")
            address = base.get("address")

            if not symbol or not address:
                continue

            if address in seen_tokens:
                continue

            liquidity = pair.get("liquidity", {}).get("usd", 0)
            volume = pair.get("volume", {}).get("h24", 0)
            fdv = pair.get("fdv", 0)
            url = pair.get("url")

            if liquidity < 5000:
                continue

            if fdv and fdv > 100000:
                continue

            seen_tokens.add(address)

            message = f"""
🚨 WEB3RAY ALPHA V2

🪙 Token: {symbol}

📄 CA:
{address}

💰 FDV:
${fdv}

💧 Liquidity:
${liquidity}

📈 Volume 24h:
${volume}

🔗 Chart:
{url}
"""

            telegram_url = f"https://api.telegram.org/bot{token}/sendMessage"

            requests.post(
                telegram_url,
                data={
                    "chat_id": chat_id,
                    "text": message
                }
            )

            print(message)

            sent += 1

            if sent >= 3:
                break

        print("✅ SCAN COMPLETE")

    except Exception as e:
        print("ERROR:", e)
