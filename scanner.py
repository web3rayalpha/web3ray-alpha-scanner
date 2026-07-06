import requests

def get_new_tokens():
    print("🔍 Starting scan...")

    url = "https://api.dexscreener.com/latest/dex/search?q=solana"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()

        print("RAW DATA KEYS:", data.keys())

        pairs = data.get("pairs", [])

        print("TOTAL PAIRS FOUND:", len(pairs))

        for i, pair in enumerate(pairs[:5]):
            base = pair.get("baseToken", {})
            print(i, base.get("symbol"), pair.get("priceUsd"))

    except Exception as e:
        print("ERROR:", e)
