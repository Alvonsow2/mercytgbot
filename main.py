import os
import requests
import json
from flask import Flask, request, jsonify

# Crypto Merchant Configuration (from environment variables or config)
CRYPTO_API_KEY = os.environ.get("CRYPTO_API_KEY", "your_merchant_api_key")
CRYPTO_MERCHANT_ID = os.environ.get("CRYPTO_MERCHANT_ID", "your_merchant_id")
SERVER_URL = os.environ.get("SERVER_URL", "https://mercytgbot.onrender.com")  # Your Render URL

def create_crypto_invoice(user_id: int, amount_usd: float):
    """
    Creates an invoice using a Crypto Gateway API (e.g., OxaPay or Cryptomus).
    Returns the payment URL.
    """
    url = "https://api.oxapay.com/merchants/request"  # Example using OxaPay API
    payload = {
        "merchant": CRYPTO_API_KEY,
        "amount": amount_usd,
        "currency": "USD",
        "lifeTime": 30,  # Invoice active for 30 mins
        "feePaidByPayer": 1,
        "callbackUrl": f"{SERVER_URL}/webhook/crypto",
        "orderId": f"order_{user_id}",
        "description": "Mercy TG Bot VIP Subscription"
    }
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        if data.get("result") == 100:
            return data.get("payLink")
    except Exception as e:
        print(f"Error generating crypto invoice: {e}")
    return None

# Add Command Handler for Telegram
async def crypto_deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    amount = 10.0  # Set standard VIP subscription rate or parse from context.args
    
    pay_url = create_crypto_invoice(user_id, amount)
    
    if pay_url:
        reply_markup = {
            "inline_keyboard": [
                [{"text": "💳 Pay $10 via Crypto (USDT/BTC)", "url": pay_url}]
            ]
        }
        await update.message.reply_text(
            "Click the button below to complete your crypto payment. Access will be activated automatically upon confirmation:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("⚠️ Unable to generate crypto invoice at the moment. Please try again later.")

# Flask Webhook Endpoint to handle payment confirmations
@app.route('/webhook/crypto', methods=['POST'])
def crypto_webhook():
    data = request.json
    # Process webhook payment confirmation
    if data and data.get("status") == "paid":
        order_id = data.get("orderId")  # Contains order_USERID
        user_id = order_id.split("_")[1]
        
        # TODO: Activate user status in database / send welcome notification
        print(f"Payment confirmed for Telegram User ID: {user_id}")
        return jsonify({"status": "ok"}), 200

    return jsonify({"status": "ignored"}), 200
