import requests

def get_new_tokens():
    print("🔍 Scanner running safely...")

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

        print("SCAN COMPLETE")

    except Exception as e:
        print("ERROR:", str(e))
