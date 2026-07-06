import requests

def get_new_tokens():
    print("🔍 START SCAN")

    url = "https://api.dexscreener.com/latest/dex/search?q=solana"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()

        pairs = data.get("pairs", [])

        print("TOTAL PAIRS FOUND:", len(pairs))

        # FORCE SHOW FIRST 10 RAW TOKENS (NO FILTERS)
        for i, pair in enumerate(pairs[:10]):
            base = pair.get("baseToken", {})
            symbol = base.get("symbol")
            price = pair.get("priceUsd")

            print(f"[{i}] {symbol} -> {price}")

        print("SCAN COMPLETE")

    except Exception as e:
        print("ERROR:", e)
