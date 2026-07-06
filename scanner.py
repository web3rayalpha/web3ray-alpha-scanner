import requests

def get_new_tokens(bot, chat_id):
    print("🔍 SCANNING ALPHA TOKENS")

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

            if not symbol:
                continue

            # filter noise
            if symbol in ["SOL", "USDC", "USDT"]:
                continue

            if liquidity and liquidity < 100000:
                continue

            msg = (
                f"🚨 WEB3RAY SIGNAL\n\n"
                f"Token: {symbol}\n"
                f"Price: ${price}\n"
                f"Liquidity: ${liquidity}"
            )

            print(msg)

            bot.send_message(chat_id=int(chat_id), text=msg)

            sent += 1
            if sent >= 3:
                break

        print("SCAN COMPLETE")

    except Exception as e:
        print("ERROR:", str(e))
