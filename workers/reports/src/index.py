from js import fetch
import json
import sys
from datetime import datetime

# Local database import (bundled in src/)
from database import Database

async def on_scheduled(event, env):
    """
    Cloudflare Cron Worker: Daily Business Reports
    """
    admin_id = getattr(env, "ADMIN_USER_IDS", "").split(",")[0].strip()
    bot_token = env.TELEGRAM_BOT_TOKEN
    db_url = env.DATABASE_URL
    
    if not bot_token or not admin_id or not db_url:
        return

    try:
        db = Database(db_url)
        today = await db.get_today_stats()
        weekly = await db.get_weekly_stats()
        top_products = await db.get_top_products(days=1, limit=5)
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        report_text = (
            f"📊 *DAILY BUSINESS REPORT* ({date_str})\n"
            "═══════════════════════════════\n\n"
            f"*KPIs:*\n📦 Orders: {today.get('order_count', 0)}\n💰 Revenue: ৳{today.get('total_revenue', 0):,.2f}\n\n"
            f"*WEEKLY:*\n📦 Orders: {weekly.get('order_count', 0)}\n💰 Revenue: ৳{weekly.get('total_revenue', 0):,.2f}"
        )
        
        await send_telegram_msg(bot_token, admin_id, report_text)
    except Exception as e:
        print(f"Reports Error: {e}")

async def send_telegram_msg(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    await fetch(url, {
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
    })
