import os
import time
from scanner_v5 import get_new_tokens


def main():
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    if not token or not chat_id:
        print("Missing BOT_TOKEN or CHAT_ID")
        return

    print("WEB3RAY V5 STARTED")

    while True:
        try:
            get_new_tokens(token, chat_id)
        except Exception as e:
            print("ERROR:", e)

        time.sleep(30)


if __name__ == "__main__":
    main()
