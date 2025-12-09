import os
import telebot
import requests
import json
from datetime import datetime
from flask import Flask
from threading import Thread

# توکن ربات تو
TOKEN = "8369300215:AAFWNkTzr1WT5afA7FmT0ZKKuSSEWAfloKM"
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

print("🤖 ربات تحلیل ارز دیجیتال در حال راه‌اندازی...")

# ========== دستورات اصلی ==========
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """
🚀 **ربات تحلیل ارز دیجیتال** 🚀

📊 **دستورات موجود:**

💰 /price [ارز] - قیمت لحظه‌ای
   مثال: /price bitcoin
   مثال: /price ethereum,bitcoin

🏆 /top10 - 10 ارز برتر بازار

📈 /signal [ارز] - تحلیل و سیگنال
   مثال: /signal bitcoin

🔔 /alert - تنظیم هشدار قیمت

📱 درباره ربات: @SignalMSAbot
"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown')
    print(f"✅ کاربر {message.from_user.username} ربات را شروع کرد")

@bot.message_handler(commands=['price'])
def get_price(message):
    try:
        # دریافت ارز از پیام
        text = message.text.split()
        if len(text) > 1:
            coins = text[1].lower()
        else:
            coins = 'bitcoin,ethereum,ripple'
        
        # دریافت قیمت از CoinGecko
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': coins,
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        result = "💰 **قیمت لحظه‌ای:**\n\n"
        for coin, info in data.items():
            price = info['usd']
            change = info.get('usd_24h_change', 0)
            change_icon = "📈" if change > 0 else "📉"
            result += f"• **{coin.upper()}**: ${price:,.2f}\n"
            result += f"  تغییر 24h: {change_icon} {change:+.2f}%\n\n"
        
        result += f"⏰ {datetime.now().strftime('%H:%M')}"
        bot.reply_to(message, result, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)[:100]}")
        print(f"خطا در دریافت قیمت: {e}")

@bot.message_handler(commands=['top10'])
def top_coins(message):
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 10,
            'page': 1
        }
        
        response = requests.get(url, params=params, timeout=15)
        coins = response.json()
        
        result = "🏆 **10 ارز برتر بازار:**\n\n"
        for i, coin in enumerate(coins, 1):
            symbol = coin['symbol'].upper()
            name = coin['name']
            price = coin['current_price']
            change = coin['price_change_percentage_24h']
            
            emoji = "🟢" if change > 0 else "🔴"
            
            result += f"{i}. **{name}** ({symbol})\n"
            result += f"   💵 ${price:,.2f}\n"
            result += f"   📊 {emoji} {change:+.2f}%\n\n"
        
        result += f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        bot.reply_to(message, result, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)[:100]}")

@bot.message_handler(commands=['signal'])
def send_signal(message):
    try:
        text = message.text.split()
        coin = text[1].lower() if len(text) > 1 else 'bitcoin'
        
        # دریافت قیمت
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': coin,
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if coin not in data:
            bot.reply_to(message, f"❌ ارز '{coin}' پیدا نشد")
            return
        
        price = data[coin]['usd']
        change = data[coin]['usd_24h_change']
        
        # تحلیل ساده
        if change > 10:
            signal = "🟢 **خرید قوی** (رشد بالا)"
        elif change > 3:
            signal = "🟢 **خرید**"
        elif change < -10:
            signal = "🔴 **فروش قوی** (افت شدید)"
        elif change < -3:
            signal = "🔴 **فروش**"
        else:
            signal = "⚪ **خنثی** (منتظر بمان)"
        
        msg = f"""
📊 **تحلیل {coin.upper()}**

💰 قیمت فعلی: **${price:,.2f}**
📈 تغییر 24h: **{change:+.2f}%**

🔔 **سیگنال:** {signal}

⚠️ نکته: این تحلیل ساده است. قبل از معامله تحقیق کنید.

⏰ زمان: {datetime.now().strftime('%H:%M')}
"""
        bot.reply_to(message, msg, parse_mode='Markdown')
        
    except IndexError:
        bot.reply_to(message, "⚠️ لطفاً نام ارز را وارد کنید\nمثال: /signal bitcoin")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)[:100]}")

@bot.message_handler(commands=['alert'])
def set_alert(message):
    bot.reply_to(message, "🔔 این قابلیت به زودی اضافه خواهد شد")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "❓ دستور نامعتبر. از /start برای راهنما استفاده کنید.")

# ========== وب سرور ==========
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Crypto Signal Bot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Tahoma, Arial, sans-serif;
                text-align: center;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                padding: 30px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            h1 {
                font-size: 2.5em;
                margin-bottom: 20px;
            }
            .status {
                font-size: 1.5em;
                color: #4CAF50;
                margin: 20px 0;
                padding: 10px;
                background: rgba(76, 175, 80, 0.2);
                border-radius: 10px;
            }
            .bot-info {
                background: rgba(255, 255, 255, 0.2);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }
            .commands {
                text-align: left;
                background: rgba(255, 255, 255, 0.1);
                padding: 15px;
                border-radius: 10px;
                margin: 15px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Crypto Signal Bot</h1>
            <div class="status">✅ Bot is Running!</div>
            <div class="bot-info">
                <p><strong>Telegram Bot:</strong> @SignalMSAbot</p>
                <p><strong>Developer:</strong> Reza</p>
                <p><strong>Last Update:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
            </div>
            <div class="commands">
                <h3>📋 Available Commands:</h3>
                <p>/start - راهنما</p>
                <p>/price [coin] - قیمت ارز</p>
                <p>/top10 - 10 ارز برتر</p>
                <p>/signal [coin] - تحلیل سیگنال</p>
            </div>
            <p>ربات تحلیل ارزهای دیجیتال</p>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return {'status': 'running', 'bot': '@SignalMSAbot', 'time': datetime.now().isoformat()}

# ========== اجرای ربات ==========
def run_telegram_bot():
    """اجرای ربات تلگرام"""
    print("🔧 شروع ربات تلگرام...")
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        print(f"خطا در ربات: {e}")

def run_web_server():
    """اجرای وب سرور"""
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 شروع وب سرور روی پورت {port}...")
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 راه‌اندازی ربات تحلیل ارز دیجیتال")
    print("=" * 50)
    
    # اجرای ربات در thread جداگانه
    import threading
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    # اجرای وب سرور
    run_web_server()
