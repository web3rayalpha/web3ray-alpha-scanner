import os
from scanner_v5 import get_new_tokens


def main():
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    if not token:
        raise Exception("BOT_TOKEN missing")

    if not chat_id:
        raise Exception("CHAT_ID missing")

    print("WEB3RAY V5 STARTED")

    get_new_tokens(
        token=token,
        chat_id=chat_id
    )


if __name__ == "__main__":
    main()
