from js import Response, fetch
import json

async def on_scheduled(event, env):
    """
    Cloudflare Cron Worker: Monitoring Nongor Website
    Runs every 5 minutes.
    """
    website_url = getattr(env, "WEBSITE_URL", "https://nongor-brand.vercel.app")
    admin_id = getattr(env, "ADMIN_USER_IDS", "").split(",")[0].strip()
    bot_token = env.TELEGRAM_BOT_TOKEN
    
    try:
        # Check website health
        response = await fetch(website_url, {
            "method": "GET",
            "headers": {"User-Agent": "CloudflareWorker-NongorBot-Monitor/3.0"}
        })
        
        status = response.status
        
        if status >= 400:
            # Website down alert
            msg = f"🚨 *WEBSITE ALERT!*\n\nURL: {website_url}\nStatus: {status}\n\nAction required!"
            await send_telegram_alert(bot_token, admin_id, msg)
            print(f"Monitor: Alert sent for status {status}")
        else:
            print(f"Monitor: Website {website_url} is OK ({status})")
            
    except Exception as e:
        # Error during fetch
        error_msg = f"🚨 *MONITOR CRASH!*\n\nCould not reach {website_url}\nError: {str(e)}"
        await send_telegram_alert(bot_token, admin_id, error_msg)
        print(f"Monitor Error: {e}")

async def send_telegram_alert(token, chat_id, text):
    """Send alert via Telegram Bot API"""
    if not token or not chat_id: return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        await fetch(url, {
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            })
        })
    except Exception as e:
        print(f"Failed to send alert: {e}")
