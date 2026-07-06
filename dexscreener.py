import requests

URL = "https://api.dexscreener.com/latest/dex/search?q=solana"

def get_pairs():
    response = requests.get(URL, timeout=10)
    data = response.json()
    return data.get("pairs", [])
