import os
import glob
import asyncio
import threading
from collections import Counter
import pandas as pd
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ----------------------------------------------------
# 1. Configuration & Paths
# ----------------------------------------------------
TOKEN = os.environ.get("BOT_TOKEN", "8611395931:AAFY20h1K7_09jYAvGVFgjwZKH5VPank10I")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_csv_filepath():
    """Finds the CSV file dynamically in the repository."""
    target = os.path.join(BASE_DIR, "Dan_data_period_5000.csv")
    if os.path.exists(target):
        return target
    csv_files = glob.glob(os.path.join(BASE_DIR, "*.csv"))
    if csv_files:
        return csv_files[0]
    return None

# ----------------------------------------------------
# 2. Dynamic High-Probability Analysis Engine
# ----------------------------------------------------
def calculate_dynamic_top3():
    """Reads the CSV database and computes the most frequent combinations."""
    csv_path = get_csv_filepath()
    if not csv_path or not os.path.exists(csv_path):
        return None, None

    try:
        df = pd.read_csv(csv_path)
        
        # Clean column names (strip whitespace)
        df.columns = df.columns.str.strip()

        if 'Numbers' not in df.columns:
            return None, None

        # 1. Calculate overall top 3 combinations
        all_numbers = df['Numbers'].dropna().astype(str).str.strip().tolist()
        overall_counts = Counter(all_numbers)
        overall_top3 = [item[0] for item in overall_counts.most_common(3)]

        # 2. Calculate top 3 per category (if Category column exists)
        category_top3 = {}
        if 'Category' in df.columns:
            for category, group in df.groupby('Category'):
                cat_numbers = group['Numbers'].dropna().astype(str).str.strip().tolist()
                cat_counts = Counter(cat_numbers)
                category_top3[category] = [item[0] for item in cat_counts.most_common(3)]

        return overall_top3, category_top3
    except Exception as e:
        print(f"Error analyzing CSV data: {e}")
        return None, None

def generate_broadcast_message():
    """Formats the statistical analysis into a Telegram message."""
    overall_top3, category_top3 = calculate_dynamic_top3()

    if not overall_top3:
        return "⚠️ *Database is currently unavailable or missing required columns.*"

    msg = "📊 *KK HASH HIGH PROBABILITY COMBINATIONS*\n"
    msg += "───────────────────────────\n"
    msg += f"🔥 *Overall TOP 3:* `{', '.join(overall_top3)}` \n\n"
    
    if category_top3:
        msg += "🎯 *Category TOP 3:*\n"
        for cat, top_list in category_top3.items():
            msg += f"• *{cat}:* `{', '.join(top_list)}` \n"
            
    msg += "───────────────────────────\n"
    msg += "🤖 *Dynamically calculated from historical hash data.*"
    return msg

# ----------------------------------------------------
# 3. Telegram Bot Handlers
# ----------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Welcome to Mercy Betting Company!\n\n"
        "• Send any *Period number* (e.g. `5000`) to look up details.\n"
        "• Send `/top` or `/broadcast` to view high-probability combination predictions!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Replies with the dynamically calculated top combinations."""
    report = generate_broadcast_message()
    await update.message.reply_text(report, parse_mode="Markdown")

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    csv_path = get_csv_filepath()

    if not csv_path or not os.path.exists(csv_path):
        await update.message.reply_text(
            "Database is currently unavailable. Please ensure the CSV file is uploaded to GitHub."
        )
        return

    try:
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()

        # Match query against Period column or general text matching
        matched_rows = pd.DataFrame()
        
        if 'Period' in df.columns:
            matched_rows = df[df['Period'].astype(str).str.strip().str.lower() == query.lower()]

        if matched_rows.empty:
            # Fallback string search across all columns
            mask = df.astype(str).apply(lambda row: row.str.contains(query, case=False, na=False)).any(axis=1)
            matched_rows = df[mask]

        if matched_rows.empty:
            await update.message.reply_text("❌ No matching records found in our system. Try another keyword or code.")
            return

        row = matched_rows.iloc[0]
        
        # Build formatted match message
        reply_msg = "🔍 *Match Result:*\n\n"
        for col in df.columns:
            val = row[col]
            reply_msg += f"• *{col}*: {val}\n"

        await update.message.reply_text(reply_msg, parse_mode="Markdown")

    except Exception as e:
        print(f"Search error: {e}")
        await update.message.reply_text("⚠️ An error occurred while processing your request.")

# ----------------------------------------------------
# 4. Flask Keep-Alive Server for Render
# ----------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Mercy TG Bot is running live!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ----------------------------------------------------
# 5. Application Execution
# ----------------------------------------------------
def main():
    # Start Flask in a background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Build Telegram bot
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("broadcast", top_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))

    print("Starting Telegram bot polling...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
