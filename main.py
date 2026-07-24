import os
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Load dataset
CSV_FILE = "Dan_Dan_Talbot_data_period_5000.csv"

try:
    df = pd.read_csv(CSV_FILE)
    print("CSV loaded successfully!")
except Exception as e:
    print(f"Error loading CSV: {e}")
    df = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Mercy Betting Company! Type a query or code to search our database.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    
    if df is None:
        await update.message.reply_text("Database is currently unavailable.")
        return

    # Search CSV (searches across all columns for matching text)
    matches = df[df.apply(lambda row: row.astype(str).str.contains(user_text, case=False).any(), axis=1)]

    if not matches.empty:
        # Get the first matching result (or format top results)
        result_str = ""
        for col in matches.columns:
            result_str += f"*{col}*: {matches.iloc[0][col]}\n"
        
        await update.message.reply_text(result_str, parse_mode="Markdown")
    else:
        await update.message.reply_text("No matching records found for your query. Please try again.")

if _name_ == '_main_':
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is polling...")
    app.run_polling()
