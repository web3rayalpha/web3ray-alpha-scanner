 import requests

def get_new_tokens():
    print("🔍 Starting scan safely...")

    url = "https://api.dexscreener.com/latest/dex/search?q=solana"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()

        pairs = data.get("pairs", [])

        print(f"TOTAL PAIRS FOUND: {len(pairs)}")

        count = 0

        for pair in pairs:
            base = pair.get("baseToken", {})
            symbol = base.get("symbol")
            price = pair.get("priceUsd")

            # ignore noise
            if not symbol or symbol == "SOL":
                continue

            print(f"{symbol} | ${price}")

            count += 1
            if count >= 10:
                break

        print("WEB3RAY SCAN COMPLETE")

    except Exception as e:
        print("SCAN ERROR:", str(e))
