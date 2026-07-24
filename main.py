import os
import glob
import asyncio
import threading
from collections import Counter
import pandas as pd
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
# 2. Chinese-Exact High Probability Calculation Engine
# ----------------------------------------------------
def calculate_dynamic_top3():
    """Reads the CSV database and computes the most frequent combinations matching Chinese categories."""
    csv_path = get_csv_filepath()
    if not csv_path or not os.path.exists(csv_path):
        return None, None

    try:
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()

        if 'Numbers' not in df.columns:
            return None, None

        # 1. Calculate overall top 3 combinations
        all_numbers = df['Numbers'].dropna().astype(str).str.strip().tolist()
        overall_counts = Counter(all_numbers)
        overall_top3 = [item[0] for item in overall_counts.most_common(3)]

        # 2. Map standard categories to exact Chinese script labels (dd, xd, xs, ds)
        category_mapping = {
            "Big Odd": "dd (大单)",
            "Large Single": "dd (大单)",
            "Small Odd": "xd (小单)",
            "Small Single": "xd (小单)",
            "Small Even": "xs (小双)",
            "Small Double": "xs (小双)",
            "Big Even": "ds (大双)",
            "Large Double": "ds (大双)"
        }

        category_top3 = {
            "dd (大单)": [],
            "xd (小单)": [],
            "xs (小双)": [],
            "ds (大双)": []
        }

        if 'Category' in df.columns:
            for raw_cat, group in df.groupby('Category'):
                cat_str = str(raw_cat).strip()
                target_key = category_mapping.get(cat_str, cat_str)
                
                cat_numbers = group['Numbers'].dropna().astype(str).str.strip().tolist()
                cat_counts = Counter(cat_numbers)
                top_items = [item[0] for item in cat_counts.most_common(3)]
                
                if target_key in category_top3:
                    category_top3[target_key] = top_items
                else:
                    category_top3[target_key] = top_items

        return overall_top3, category_top3
    except Exception as e:
        print(f"Error analyzing CSV data: {e}")
        return None, None

def generate_chinese_broadcast_message():
    """Formats the statistical analysis to MATCH EXACTLY the Chinese script from screenshot 173471.jpg."""
    overall_top3, category_top3 = calculate_dynamic_top3()

    if not overall_top3 or len(overall_top3) < 3:
        # Fallback to defaults from original snippet if dataset is thin
        overall_top3 = ["0+2+9", "3+6+7", "1+5+9"]

    msg = "==================================================\n"
    msg += "【KK哈希高概率组合自动播报】\n"
    msg += f"整体TOP3高概率组合: {overall_top3[0]}、{overall_top3[1]}、{overall_top3[2]}\n"
    
    if category_top3:
        for cat, top_list in category_top3.items():
            if len(top_list) >= 3:
                msg += f"{cat}分类TOP3: {top_list[0]}、{top_list[1]}、{top_list[2]}\n"
            elif len(top_list) > 0:
                msg += f"{cat}分类TOP3: {'、'.join(top_list)}\n"

    msg += "=================================================="
    return msg

# ----------------------------------------------------
# 3. Telegram Bot Handlers
# ----------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Welcome to Mercy Betting Company!\n\n"
        "• Send any *Period number* (e.g. `5000`) to look up details.\n"
        "• Send `/top` or `/broadcast` to view high-probability predictions.\n"
        "• Send `/topup` or `/deposit` to make a Crypto deposit."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Replies with the 100% exact Chinese broadcast format."""
    report = generate_chinese_broadcast_message()
    await update.message.reply_text(f"```\n{report}\n```", parse_mode="MarkdownV2")

async def crypto_deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates a crypto deposit invoice / wallet link."""
    user_id = update.effective_user.id
    
    # Generate a deposit invoice link (using Telegram @wallet or custom crypto gateway)
    payment_url = f"https://t.me/wallet?startattach=order_{user_id}"
    
    keyboard = [
        [InlineKeyboardButton("💳 Pay via Crypto Wallet (USDT / TON / BTC)", url=payment_url)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    deposit_msg = (
        "💎 *CRYPTO TOP-UP & DEPOSIT*\n"
        "───────────────────────────\n"
        "Select your preferred cryptocurrency to deposit:\n"
        "• *USDT (TRC-20 / TON)*\n"
        "• *Bitcoin (BTC)*\n"
        "• *TON Coin*\n\n"
        "Click the button below to initiate your deposit securely:"
    )
    await update.message.reply_text(deposit_msg, reply_markup=reply_markup, parse_mode="Markdown")

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    csv_path = get_csv_filepath()

    if not csv_path or not os.path.exists(csv_path):
        await update.message.reply_text("Database is currently unavailable.")
        return

    try:
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()

        matched_rows = pd.DataFrame()
        if 'Period' in df.columns:
            matched_rows = df[df['Period'].astype(str).str.strip().str.lower() == query.lower()]

        if matched_rows.empty:
            mask = df.astype(str).apply(lambda row: row.str.contains(query, case=False, na=False)).any(axis=1)
            matched_rows = df[mask]

        if matched_rows.empty:
            await update.message.reply_text("❌ No matching records found.")
            return

        row = matched_rows.iloc[0]
        reply_msg = "🔍 *Match Result:*\n\n"
        for col in df.columns:
            reply_msg += f"• *{col}*: {row[col]}\n"

        await update.message.reply_text(reply_msg, parse_mode="Markdown")

    except Exception as e:
        print(f"Search error: {e}")
        await update.message.reply_text("⚠️ An error occurred while searching.")

# ----------------------------------------------------
# 4. Flask Server & Webhooks
# ----------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Mercy TG Bot is running live!", 200

@app.route('/webhook/crypto', methods=['POST'])
def crypto_webhook():
    """Receives payment notifications when a user pays via Crypto."""
    data = request.json
    print(f"Payment received: {data}")
    return jsonify({"status": "ok"}), 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ----------------------------------------------------
# 5. Application Execution
# ----------------------------------------------------
def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    application = ApplicationBuilder().token(TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler(["top", "broadcast"], top_command))
    application.add_handler(CommandHandler(["topup", "deposit", "crypto", "wallet"], crypto_deposit_command))
    
    # Text Message Handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))

    print("Starting Telegram bot polling...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
