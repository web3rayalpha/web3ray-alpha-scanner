import requests

def get_new_tokens():
    print("🔍 Searching for real alpha tokens...")

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

            # FILTER OUT NOISE (IMPORTANT)
            if not symbol:
                continue
            if symbol in ["SOL", "USDC", "USDT"]:
                continue

            print(f"🚨 ALPHA: {symbol} | ${price}")

            count += 1
            if count >= 10:
                break

        print("ALPHA SCAN COMPLETE")

    except Exception as e:
        print("ERROR:", str(e))
