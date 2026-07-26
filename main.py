import os
import time
from scanner_v4 import get_new_tokens


def main():
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    api_key = os.getenv("BIRDEYE_API_KEY")

    if not token or not chat_id or not api_key:
        print("Missing BOT_TOKEN, CHAT_ID or BIRDEYE_API_KEY")
        return

    print("WEB3RAY V4 STARTED")

    while True:
        get_new_tokens(token, chat_id, api_key)
        time.sleep(30)


if __name__ == "__main__":
    main()
