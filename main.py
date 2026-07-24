import os
import glob
import asyncio
from collections import Counter
import pandas as pd
from flask import Flask, request, jsonify
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ----------------------------------------------------
# 1. Environment & Paths
# ----------------------------------------------------
TOKEN = os.environ.get("BOT_TOKEN", "8611395931:AAFY20h1K7_09jYAvGVFgjwZKH5VPank10I")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://mercytgbot.onrender.com")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

# Initialize Telegram App
telegram_app = ApplicationBuilder().token(TOKEN).build()

# ----------------------------------------------------
# 2. Data Processing Logic
# ----------------------------------------------------
def get_csv_filepath():
    target = os.path.join(BASE_DIR, "Dan_data_period_5000.csv")
    if os.path.exists(target):
        return target
    csv_files = glob.glob(os.path.join(BASE_DIR, "*.csv"))
    return csv_files[0] if csv_files else None

USER_BALANCES = {}

def calculate_dynamic_top3():
    csv_path = get_csv_filepath()
    if not csv_path or not os.path.exists(csv_path):
        return None, None
    try:
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()
        if 'Numbers' not in df.columns:
            return None, None
        all_numbers = df['Numbers'].dropna().astype(str).str.strip().tolist()
        overall_counts = Counter(all_numbers)
        overall_top3 = [item[0] for item in overall_counts.most_common(3)]
        return overall_top3, None
    except Exception as e:
        print(f"Error calculating stats: {e}")
        return None, None

def generate_chinese_broadcast_message():
    overall_top3, _ = calculate_dynamic_top3()
    if not overall_top3 or len(overall_top3) < 3:
        overall_top3 = ["0+1+2", "3+6+9", "6+1+6"]

    msg = "==================================================\n"
    msg += "【KK哈希高概率组合自动播报】\n"
    msg += f"整体TOP3高概率组合: {overall_top3[0]}、{overall_top3[1]}、{overall_top3[2]}\n"
    msg += "=================================================="
    return msg

# ----------------------------------------------------
# 3. Handlers
# ----------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [
        ["📊 高概率预测", "⏱️ 开启自动播报"],
        ["💳 加密货币充值", "📤 申请提现"],
        ["👤 个人中心", "📜 游戏规则"],
        ["👨‍💻 联系客服", "🛑 停止播报"]
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    welcome_text = (
        "🎰 欢迎使用 Mercy KK 哈希平台！\n\n"
        "请点击下方菜单按钮快速使用相关功能："
    )
    await update.message.reply_text(welcome_text, reply_markup=markup)

async def crypto_deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payment_url = f"https://t.me/wallet?startattach=order_{user_id}"
    keyboard = [[InlineKeyboardButton("💳 通过加密钱包支付 (USDT / TON / BTC)", url=payment_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    deposit_msg = (
        "💎 加密货币充值通道\n"
        "───────────────────────────\n"
        "请选择您要充值的加密货币币种：\n"
        "• USDT (TRC-20 / TON)\n"
        "• 比特币 (BTC)\n"
        "• TON Coin\n\n"
        "点击下方按钮进行即时充值："
    )
    await update.message.reply_text(deposit_msg, reply_markup=reply_markup)

async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    withdraw_msg = (
        "📤 加密货币提现\n"
        "───────────────────────────\n"
        "如需申请提现，请按照以下格式直接回复指令：\n\n"
        "/withdraw [金额] [USDT_TRC20收款地址]\n\n"
        "示例：\n/withdraw 50 T9xXX...xxxx"
    )
    await update.message.reply_text(withdraw_msg)

async def account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    balance = USER_BALANCES.get(user.id, 0.00)
    account_msg = (
        f"👤 个人中心\n"
        f"───────────────────────────\n"
        f"• 用户姓名: {user.first_name} ({user.id})\n"
        f"• 账户余额: {balance:.2f} USDT\n"
        f"• 账号状态: 正常 ✅\n\n"
        f"点击 💳 加密货币充值 可快速添加资金。"
    )
    await update.message.reply_text(account_msg)

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = (
        "📜 KK 哈希玩法说明与分类规则\n"
        "───────────────────────────\n"
        "• dd (大单): 尾数为 5、7、9\n"
        "• xd (小单): 尾数为 1、3\n"
        "• xs (小双): 尾数为 0、2、4\n"
        "• ds (大双): 尾数为 6、8\n\n"
        "系统将根据实时期数数据算法自动更新并预测高概率组合。"
    )
    await update.message.reply_text(rules_text)

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("💬 联系在线客服", url="https://t.me/telegram")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👨‍💻 需要帮助？点击下方按钮直通专职客服：", reply_markup=reply_markup)

async def handle_text_and_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()

    if text in ["📊 高概率预测", "/top", "/broadcast"]:
        report = generate_chinese_broadcast_message()
        await update.message.reply_text(f"```\n{report}\n```", parse_mode="MarkdownV2")
    elif text in ["💳 加密货币充值", "/deposit"]:
        await crypto_deposit_command(update, context)
    elif text in ["📤 申请提现", "/withdraw"]:
        await withdraw_command(update, context)
    elif text in ["👤 个人中心", "/balance"]:
        await account_command(update, context)
    elif text in ["📜 游戏规则", "/rules"]:
        await rules_command(update, context)
    elif text in ["👨‍💻 联系客服", "/support"]:
        await support_command(update, context)
    else:
        await update.message.reply_text("✅ 指令已接收。请使用菜单按钮导航。")

# Register handlers to app
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler(["topup", "deposit", "crypto"], crypto_deposit_command))
telegram_app.add_handler(CommandHandler("withdraw", withdraw_command))
telegram_app.add_handler(CommandHandler(["balance", "profile"], account_command))
telegram_app.add_handler(CommandHandler("rules", rules_command))
telegram_app.add_handler(CommandHandler("support", support_command))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_and_buttons))

# ----------------------------------------------------
# 4. Flask Webhook Receiver
# ----------------------------------------------------
@app.route("/", methods=["GET"])
def health_check():
    return "Mercy TG Bot Webhook Active", 200

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    """Receives updates pushed directly from Telegram."""
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, telegram_app.bot)
        
        asyncio.run(telegram_app.initialize())
        asyncio.run(telegram_app.process_update(update))
        asyncio.run(telegram_app.shutdown())
    except Exception as e:
        print(f"Webhook Execution Error: {e}")
    return "OK", 200

def set_telegram_webhook():
    """Registers the Render URL with Telegram's Webhook API."""
    import urllib.request
    clean_url = RENDER_URL.rstrip('/')
    webhook_endpoint = f"{clean_url}/webhook/{TOKEN}"
    api_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_endpoint}&drop_pending_updates=true"
    
    try:
        req = urllib.request.Request(api_url)
        with urllib.request.urlopen(req) as resp:
            print(f"Webhook set successfully: {resp.read().decode('utf-8')}")
    except Exception as e:
        print(f"Failed setting webhook: {e}")

if __name__ == "__main__":
    set_telegram_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
