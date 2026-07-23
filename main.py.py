import os
import asyncio
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging to see errors in the Render deployment logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------------------------------------------
# 1. FLASK WEB SERVER (Keeps Render Free Tier Alive)
# ----------------------------------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running 24/7!", 200

@app.route("/health")
def health():
    return "OK", 200

def run_flask():
    # Render automatically sets the PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ----------------------------------------------------
# 2. TELEGRAM BOT HANDLERS
# ----------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user.first_name
    await update.message.reply_text(f"Hello {user}! I am live on Render 24/7.")

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echoes back any text message sent to the bot."""
    await update.message.reply_text(f"You said: {update.message.text}")

# ----------------------------------------------------
# 3. MAIN EXECUTION
# ----------------------------------------------------
def main():
    # Read the token from Environment Variables set on Render
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN environment variable is missing!")
        return

    # Start Flask web server in a separate background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask web server started.")

    # Initialize Telegram Bot Application
    application = Application.builder().token(token).build()

    # Add command & message handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))

    # Start polling for incoming Telegram messages
    logger.info("Starting Telegram bot polling...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()