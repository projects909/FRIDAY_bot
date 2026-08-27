import os
from collections import defaultdict, deque

from flask import Flask
from threading import Thread

from openai import OpenAI
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)

# Keeps the most recent messages from each group in memory
chat_history = defaultdict(lambda: deque(maxlen=30))

SYSTEM_PROMPT = """
You are FRIDAY, an AI assistant who is a member of a Telegram group chat.

Your personality is intelligent, concise, confident, helpful, and natural.
Talk like a member of the group, not like a customer-service chatbot.

You can see recent messages in the conversation for context.
Only answer the question being directed to you.
Do not constantly explain that you are an AI.
"""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if not message or not message.text:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user

    name = user.first_name if user else "Someone"
    text = message.text

    # Save every message for conversational context
    chat_history[chat_id].append(f"{name}: {text}")

    # FRIDAY responds when someone says "Friday"
    if "friday" not in text.lower():
        return

    recent_conversation = "\n".join(chat_history[chat_id])

    prompt = f"""
Here is the recent group conversation:

{recent_conversation}

Respond naturally to the latest message directed at you.
"""

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            instructions=SYSTEM_PROMPT,
            input=prompt,
        )

        answer = response.output_text

        await message.reply_text(answer)

        chat_history[chat_id].append(f"FRIDAY: {answer}")

    except Exception as e:
        print(f"Error: {e}")
        await message.reply_text("Something went wrong on my end.")

def run_bot():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    application.run_polling()

# Tiny web server so Render sees an active web service
web = Flask(__name__)

@web.route("/")
def home():
    return "FRIDAY is online."
if __name__ == "__main__":
    Thread(target=run_bot, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)
def run_web():
    port = int(os.environ.get("PORT", 10000))
    web.run(
        host="0.0.0.0",
        port=port,
        use_reloader=False
    )

if __name__ == "__main__":
    # Run Render's web server in the background
    Thread(target=run_web, daemon=True).start()

    # Telegram MUST run on the main thread
    run_bot()
