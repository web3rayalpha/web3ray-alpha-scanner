import os
import time
from scanner_v2 import get_new_tokens

def main():
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    if not token or not chat_id:
        print("Missing BOT_TOKEN or CHAT_ID")
        return

    print("WEB3RAY BOT STARTED")

    while True:
        get_new_tokens(token, chat_id)
        time.sleep(30)

if __name__ == "__main__":
    main()
