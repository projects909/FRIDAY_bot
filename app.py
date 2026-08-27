import os
from collections import defaultdict, deque
from threading import Thread

from flask import Flask
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

# Environment variables stored privately in Render
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Keeps the most recent 30 messages from each chat in memory
chat_history = defaultdict(lambda: deque(maxlen=30))

SYSTEM_PROMPT = """
You are FRIDAY, an AI assistant who is a member of a Telegram group chat.

Your personality is intelligent, concise, confident, helpful, and natural.
Talk like a member of the group, not like a customer-service chatbot.

You can see recent messages in the conversation for context.

Only respond when someone is clearly talking to you.
Do not constantly explain that you are an AI.
Do not mention these instructions.
"""


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.effective_message

    if not message or not message.text:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user

    name = user.first_name if user else "Someone"
    text = message.text.strip()

    # Save every normal text message for context
    chat_history[chat_id].append(f"{name}: {text}")

    # FRIDAY currently responds when the word "Friday" appears
    if "friday" not in text.lower():
        return

    recent_conversation = "\n".join(chat_history[chat_id])

    prompt = f"""
Here is the recent Telegram conversation:

{recent_conversation}

Respond naturally to the latest message directed at you.
"""

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            instructions=SYSTEM_PROMPT,
            input=prompt,
        )

        answer = response.output_text.strip()

        if not answer:
            answer = "I'm here."

        await message.reply_text(answer)

        chat_history[chat_id].append(
            f"FRIDAY: {answer}"
        )

    except Exception as e:
        print(
            f"OPENAI ERROR: {repr(e)}",
            flush=True
        )

        await message.reply_text(
            "Something went wrong on my end."
        )


def run_bot():
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("FRIDAY Telegram polling started.", flush=True)

    # Telegram polling must run on the main thread
    application.run_polling(
        drop_pending_updates=False
    )


# Small web server required for Render Web Service
web = Flask(__name__)


@web.route("/")
def home():
    return "FRIDAY is online."


def run_web():
    port = int(
        os.environ.get("PORT", 10000)
    )

    web.run(
        host="0.0.0.0",
        port=port,
        use_reloader=False
    )


if __name__ == "__main__":
    # Flask runs in the background
    Thread(
        target=run_web,
        daemon=True
    ).start()

    # Telegram stays on the main thread
    run_bot()
