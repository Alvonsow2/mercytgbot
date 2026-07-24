import os
import glob
import asyncio
import threading
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
# 1. Configuration & Paths
# ----------------------------------------------------
TOKEN = os.environ.get("BOT_TOKEN", "8611395931:AAFY20h1K7_09jYAvGVFgjwZKH5VPank10I")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_csv_filepath():
    target = os.path.join(BASE_DIR, "Dan_data_period_5000.csv")
    if os.path.exists(target):
        return target
    csv_files = glob.glob(os.path.join(BASE_DIR, "*.csv"))
    if csv_files:
        return csv_files[0]
    return None

USER_BALANCES = {}

# ----------------------------------------------------
# 2. Chinese-Exact High Probability Engine
# ----------------------------------------------------
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

        return overall_top3, category_top3
    except Exception as e:
        print(f"Error analyzing CSV data: {e}")
        return None, None

def generate_chinese_broadcast_message():
    overall_top3, category_top3 = calculate_dynamic_top3()

    if not overall_top3 or len(overall_top3) < 3:
        overall_top3 = ["0+1+2", "3+6+9", "6+1+6"]

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
# 3. Repeating Background Job
# ----------------------------------------------------
async def auto_broadcast_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    report = generate_chinese_broadcast_message()
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"```\n{report}\n```",
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        print(f"Auto-broadcast error: {e}")

# ----------------------------------------------------
# 4. Command & Button Handlers
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
        "🎰 *欢迎使用 Mercy KK 哈希平台！*\n\n"
        "请点击下方菜单按钮快速使用相关功能："
    )
    await update.message.reply_text(welcome_text, reply_markup=markup, parse_mode="Markdown")

async def crypto_deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payment_url = f"https://t.me/wallet?startattach=order_{user_id}"
    
    keyboard = [
        [InlineKeyboardButton("💳 通过加密钱包支付 (USDT / TON / BTC)", url=payment_url)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    deposit_msg = (
        "💎 *加密货币充值通道*\n"
        "───────────────────────────\n"
        "请选择您要充值的加密货币币种：\n"
        "• *USDT (TRC-20 / TON)*\n"
        "• *比特币 (BTC)*\n"
        "• *TON Coin*\n\n"
        "点击下方按钮进行即时充值："
    )
    await update.message.reply_text(deposit_msg, reply_markup=reply_markup, parse_mode="Markdown")

async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    withdraw_msg = (
        "📤 *加密货币提现*\n"
        "───────────────────────────\n"
        "如需申请提现，请按照以下格式直接回复指令：\n\n"
        "`/withdraw [金额] [USDT_TRC20收款地址]`\n\n"
        "示例：\n`/withdraw 50 T9xXX...xxxx`"
    )
    await update.message.reply_text(withdraw_msg, parse_mode="Markdown")

async def account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    balance = USER_BALANCES.get(user.id, 0.00)
    
    account_msg = (
        f"👤 *个人中心*\n"
        f"───────────────────────────\n"
        f"• *用户姓名:* {user.first_name} (`{user.id}`)\n"
        f"• *账户余额:* `{balance:.2f} USDT`\n"
        f"• *账号状态:* 正常 ✅\n\n"
        f"点击 *💳 加密货币充值* 可快速添加资金。"
    )
    await update.message.reply_text(account_msg, parse_mode="Markdown")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = (
        "📜 *KK 哈希玩法说明与分类规则*\n"
        "───────────────────────────\n"
        "• *dd (大单):* 尾数为 5、7、9\n"
        "• *xd (小单):* 尾数为 1、3\n"
        "• *xs (小双):* 尾数为 0、2、4\n"
        "• *ds (大双):* 尾数为 6、8\n\n"
        "系统将根据实时期数数据算法自动更新并预测高概率组合。"
    )
    await update.message.reply_text(rules_text, parse_mode="Markdown")

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💬 联系在线客服", url="https://t.me/telegram")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👨‍💻 需要帮助？点击下方按钮直通专职客服：", reply_markup=reply_markup)

async def handle_text_and_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if text in ["📊 高概率预测", "📊 High-Prob Predictions", "/top", "/broadcast"]:
        report = generate_chinese_broadcast_message()
        await update.message.reply_text(f"```\n{report}\n```", parse_mode="MarkdownV2")

    elif text in ["⏱️ 开启自动播报", "⏱️ Start Auto Broadcast", "⏱️ Start Auto Broadcast (4 Min)"]:
        if not context.job_queue:
            await update.message.reply_text("⚠️ JobQueue 正在初始化，请确保已配置 python-telegram-bot[job-queue]。")
            return

        current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
        for job in current_jobs:
            job.schedule_removal()

        context.job_queue.run_repeating(
            auto_broadcast_job,
            interval=240,
            first=1,
            chat_id=chat_id,
            name=str(chat_id)
        )
        await update.message.reply_text("✅ *已开启每 4 分钟自动高概率播报！*", parse_mode="Markdown")

    elif text in ["🛑 停止播报", "🛑 Stop Broadcast", "🛑 Stop Auto Broadcast"]:
        if not context.job_queue:
            await update.message.reply_text("ℹ️ 播报组件未激活。")
            return

        current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
        if not current_jobs:
            await update.message.reply_text("ℹ️ 当前没有运行中的自动播报任务。")
            return
        for job in current_jobs:
            job.schedule_removal()
        await update.message.reply_text("🛑 *已成功停止自动播报。*", parse_mode="Markdown")

    elif text in ["💳 加密货币充值", "💳 Crypto Deposit", "/topup", "/deposit", "/crypto"]:
        await crypto_deposit_command(update, context)

    elif text in ["📤 申请提现", "📥 Withdraw Funds", "📤 Withdraw Funds", "/withdraw"]:
        await withdraw_command(update, context)

    elif text in ["👤 个人中心", "👤 My Account", "/balance", "/profile"]:
        await account_command(update, context)

    elif text in ["📜 游戏规则", "📜 Game Rules", "/rules"]:
        await rules_command(update, context)

    elif text in ["👨‍💻 联系客服", "👨‍💻 Support", "/support"]:
        await support_command(update, context)

    else:
        csv_path = get_csv_filepath()
        if not csv_path or not os.path.exists(csv_path):
            await update.message.reply_text("数据库暂时不可用。")
            return

        try:
            df = pd.read_csv(csv_path)
            df.columns = df.columns.str.strip()

            matched_rows = pd.DataFrame()
            if 'Period' in df.columns:
                matched_rows = df[df['Period'].astype(str).str.strip().str.lower() == text.lower()]

            if matched_rows.empty:
                mask = df.astype(str).apply(lambda row: row.str.contains(text, case=False, na=False)).any(axis=1)
                matched_rows = df[mask]

            if matched_rows.empty:
                await update.message.reply_text("❌ 无法识别指令。请点击上方菜单按钮或输入有效的期号查询。")
                return

            row = matched_rows.iloc[0]
            reply_msg = "🔍 *期号查询结果：*\n\n"
            for col in df.columns:
                reply_msg += f"• *{col}*: {row[col]}\n"

            await update.message.reply_text(reply_msg, parse_mode="Markdown")

        except Exception as e:
            print(f"Search error: {e}")
            await update.message.reply_text("⚠️ 查询过程中发生错误。")

# ----------------------------------------------------
# 5. Flask Web Server
# ----------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Mercy TG Bot is running live!", 200

@app.route('/webhook/crypto', methods=['POST'])
def crypto_webhook():
    return jsonify({"status": "ok"}), 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ----------------------------------------------------
# 6. Main Application Execution
# ----------------------------------------------------
def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler(["top", "broadcast"], handle_text_and_buttons))
    application.add_handler(CommandHandler(["topup", "deposit", "crypto", "wallet"], crypto_deposit_command))
    application.add_handler(CommandHandler("withdraw", withdraw_command))
    application.add_handler(CommandHandler(["balance", "profile"], account_command))
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("support", support_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_and_buttons))

    print("Starting Telegram bot polling...")
    application.run_polling(drop_pending_updates=True, poll_interval=1.0)

if __name__ == "__main__":
    main()
