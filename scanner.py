import requests

def get_new_tokens():
    print("🔍 Scanning Solana alpha opportunities...")

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
            liquidity = pair.get("liquidity", {}).get("usd", 0)

            if not symbol:
                continue

            # stricter alpha filter
            if symbol in ["SOL", "USDC", "USDT"]:
                continue

            if liquidity and liquidity < 5000:
                continue

            print(f"🚨 ALPHA TOKEN: {symbol} | ${price} | LIQ: ${liquidity}")

            count += 1
            if count >= 10:
                break

        print("SCAN COMPLETE")

    except Exception as e:
        print("ERROR:", str(e))
