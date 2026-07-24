import os
import threading
import pandas as pd
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- FLASK WEBSERVER FOR RENDER HEALTH CHECK ---
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "Mercy Betting Bot is Live 24/7!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

# --- LOAD CSV DATASET ---
CSV_FILE = "Dan_data_5000.csv"

try:
    df = pd.read_csv(CSV_FILE)
    print("CSV loaded successfully!")
except Exception as e:
    print(f"Error loading CSV: {e}")
    df = None

# --- TELEGRAM BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Mercy Betting Company! Type a query or match code to search our database.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    
    if df is None:
        await update.message.reply_text("Database is currently unavailable.")
        return

    # Case-insensitive search across all CSV columns
    matches = df[df.apply(lambda row: row.astype(str).str.contains(user_text, case=False).any(), axis=1)]

    if not matches.empty:
        # Format top match nicely
        first_match = matches.iloc[0]
        result_str = "🔍 **Match Result:**\n\n"
        for col in matches.columns:
            result_str += f"• **{col}**: {first_match[col]}\n"
        
        await update.message.reply_text(result_str, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ No matching records found in our system. Try another keyword or code.")

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    TOKEN = os.getenv("BOT_TOKEN")
    
    # Start Flask in background thread
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Start Telegram Bot Polling
    telegram_app = ApplicationBuilder().token(TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Starting Telegram bot polling...")
    telegram_app.run_polling()
