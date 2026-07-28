import os
import time
from scanner_v6 import get_new_pools


def main():
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    api_key = os.getenv("COINGECKO_API_KEY")

    if not token:
        raise Exception("BOT_TOKEN missing")

    if not chat_id:
        raise Exception("CHAT_ID missing")

    if not api_key:
        raise Exception("COINGECKO_API_KEY missing")

    print("WEB3RAY V6 STARTED")

    while True:
        try:
            get_new_pools(
                token=token,
                chat_id=chat_id,
                api_key=api_key
            )
        except Exception as e:
            print("ERROR:", e)

        time.sleep(60)


if __name__ == "__main__":
    main()
