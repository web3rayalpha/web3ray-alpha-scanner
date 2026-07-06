import os
import time
from telegram import Bot
from scanner import get_new_tokens

def main():
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    if not token or not chat_id:
        print("Missing BOT_TOKEN or CHAT_ID")
        return

    bot = Bot(token=token)

    print("Bot connected:", bot.get_me().username)

    while True:
        get_new_tokens(bot, chat_id)
        time.sleep(30)

if __name__ == "__main__":
    main()
