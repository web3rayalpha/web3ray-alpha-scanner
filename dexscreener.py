import requests

URL = "https://api.dexscreener.com/latest/dex/search?q=raydium"

def get_pairs():
    try:
        response = requests.get(URL, timeout=10)
        data = response.json()
        return data.get("pairs", [])
    except Exception as e:
        print("Dexscreener error:", e)
        return []
