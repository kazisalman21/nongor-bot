import logging
import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import Database (Standard Version)
# Ensure bot_standard is in path or run from root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import Database

# 3rd Party Imports (Standard)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
import google.generativeai as genai
import csv
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ===============================================
# GLOBAL STATE & CONFIG
# ===============================================

ADMIN_USER_IDS = [
    int(i.strip()) for i in os.getenv("ADMIN_USER_IDS", "").split(",") 
    if i.strip().isdigit()
]
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_URL = os.getenv("NETLIFY_DATABASE_URL")

if not DATABASE_URL:
    logger.error("NETLIFY_DATABASE_URL is missing in .env!")
    sys.exit(1)

# Initialize Database
db = Database(DATABASE_URL)

# Initialize AI
ai_initialized = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        ai_initialized = True
    except Exception as e:
        logger.error(f"AI initialization failed: {e}")

CONTACT_INFO = {
    'whatsapp': '+880 1616-510037',
    'website': 'https://nongor-brand.vercel.app',
    'facebook': 'https://www.facebook.com/profile.php?id=61582283911710',
    'email': 'nongorr.anika@gmail.com',
    'phone': '+880 1616-510037'
}

BUSINESS_HOURS = {
    "weekdays": {"days": "Saturday - Thursday", "hours": "10:00 AM - 8:00 PM"},
    "friday": {"days": "Friday", "hours": "Closed"},
    "response_times": {"whatsapp": "5-10 minutes", "email": "24 hours"}
}

DELIVERY_POLICIES = {
    "dhaka": {"time": "1-2 days", "charge": 60, "free_above": 1000},
    "outside": {"time": "3-5 days", "charge": 120, "free_above": 2000}
}

# ===============================================
# SESSION MANAGEMENT
# ===============================================

class UserSession:
    def __init__(self, user_id, username=None, first_name=None):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.role = "admin" if user_id in ADMIN_USER_IDS else "user"
        self.state = "menu"
        self.last_activity = datetime.now()

user_sessions = {}

def get_session(user_id, username=None, first_name=None):
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id, username, first_name)
    return user_sessions[user_id]

# ===============================================
# KEYBOARDS
# ===============================================

def get_admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard"),
         InlineKeyboardButton("📈 Sales Chart", callback_data="admin_chart")],
        [InlineKeyboardButton("📦 Orders", callback_data="admin_orders"),
         InlineKeyboardButton("📤 Export CSV", callback_data="admin_export")],
        [InlineKeyboardButton("💰 Sales", callback_data="admin_sales"),
         InlineKeyboardButton("📉 Inventory", callback_data="admin_inventory")],
        [InlineKeyboardButton("◀️ Home", callback_data="back_menu")]
    ])

def get_user_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Chat with AI", callback_data="user_ai_chat")],
        [InlineKeyboardButton("📦 Track Order", callback_data="user_track_order"),
         InlineKeyboardButton("🛍️ Products", callback_data="user_products")],
        [InlineKeyboardButton("ℹ️ About Us", callback_data="user_about"),
         InlineKeyboardButton("📱 Contact", callback_data="user_contact")]
    ])

def get_back_button(callback_data="back_menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back to Menu", callback_data=callback_data)]])

# ===============================================
# HANDLERS
# ===============================================

async def start(update: Update, context):
    user = update.effective_user
    session = get_session(user.id, user.username, user.first_name)
    session.state = "menu"
    
    await db.save_user(user.id, user.username, user.first_name)
    
    if session.role == "admin":
        text = f"👋 Welcome back, Admin **{user.first_name}**!\nChoose an option:"
        reply_markup = get_admin_menu()
    else:
        text = f"👋 Salam, **{user.first_name}**! Welcome to Nongor Premium.\nHow can I help you today?"
        reply_markup = get_user_menu()
    
    if update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        except BadRequest:
            await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def menu(update: Update, context):
    await start(update, context)

async def help_command(update: Update, context):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_USER_IDS
    text = "📚 **ADMIN COMMANDS**\n/start, /menu, /dashboard, /export" if is_admin else \
           "📚 **USER COMMANDS**\n/start, /menu, /track, /products, /about, /contact, /support"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# Admin Handlers
async def admin_dashboard(update: Update, context):
    if update.effective_user.id not in ADMIN_USER_IDS: return
    
    today = await db.get_today_stats()
    weekly = await db.get_weekly_stats()
    users = await db.get_user_stats()
    
    text = f"📊 **BUSINESS DASHBOARD**\n\n**TODAY:**\n📦 Orders: {today.get('order_count', 0)}\n💰 Revenue: ৳{today.get('total_revenue', 0):,.2f}\n\n**WEEKLY:**\n📦 Orders: {weekly.get('order_count', 0)}\n💰 Revenue: ৳{weekly.get('total_revenue', 0):,.2f}\n\n**USERS:**\n👥 Total: {users.get('total_users', 0)}\n🔥 Active (7d): {users.get('active_users', 0)}"
    
    reply_markup = get_back_button()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def admin_orders(update: Update, context):
    if update.effective_user.id not in ADMIN_USER_IDS: return
    orders = await db.get_recent_orders(limit=10)
    
    text = "📦 **RECENT ORDERS**\n\n" + "\n".join([
        f"• #{o.get('order_id', 'N/A')} - {o.get('customer_name', 'Unknown')} - ৳{o.get('total') or 0:,.0f}" 
        for o in orders
    ]) if orders else "📦 **RECENT ORDERS**\n\nNo orders found."
    
    reply_markup = get_back_button()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def admin_sales(update: Update, context):
    if update.effective_user.id not in ADMIN_USER_IDS: return
    top = await db.get_top_products(limit=5)
    
    text = "💰 **TOP PRODUCTS**\n\n" + "\n".join([
        f"{i+1}. {p.get('product_name', 'Unknown')}: ৳{p.get('revenue', 0):,.0f}" 
        for i, p in enumerate(top)
    ]) if top else "💰 **TOP PRODUCTS**\n\nNo sales data available."
    
    reply_markup = get_back_button()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def admin_inventory(update: Update, context):
    if update.effective_user.id not in ADMIN_USER_IDS: return
    products = await db.get_available_products()
    
    text = "📉 **INVENTORY**\n\n" + "\n".join([
        f"• {p.get('name', 'Unknown')}: {p.get('order_count', 0)} orders" 
        for p in products[:15]
    ]) if products else "📉 **INVENTORY**\n\nNo products found."
    
    reply_markup = get_back_button()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# User Handlers
async def user_products(update: Update, context):
    products = await db.get_available_products()
    
    text = "🛍️ **PRODUCTS**\n\n" + "\n".join([
        f"• {p.get('name', 'Unknown')}: ৳{p.get('price', 0):,.0f}" 
        for p in products[:15]
    ]) if products else "🛍️ **PRODUCTS**\n\nNo products available at the moment."
    
    reply_markup = get_back_button()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def user_track_order(update: Update, context):
    text = "📦 **TRACK ORDER**\nPlease enter your phone number or Order ID (e.g., 01711222333 or #12345):"
    session = get_session(update.effective_user.id)
    session.state = "waiting_tracking"
    
    reply_markup = get_back_button()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def user_about(update: Update, context):
    text = f"ℹ️ **ABOUT NONGOR PREMIUM**\n═══════════════════════════════\n\n🎨 **Who We Are**\nPremium clothing brand delivering style, quality, \nand comfort to fashion-conscious individuals in BD.\n\n✨ **Our Promise**\n✅ Premium quality materials\n✅ Trendy, modern designs\n✅ Fast & reliable delivery\n\n🕐 **Business Hours**\n{BUSINESS_HOURS['weekdays']['days']}: {BUSINESS_HOURS['weekdays']['hours']}\n{BUSINESS_HOURS['friday']['days']}: {BUSINESS_HOURS['friday']['hours']}\n\n🚚 **Delivery**\n• Dhaka: {DELIVERY_POLICIES['dhaka']['time']} (৳{DELIVERY_POLICIES['dhaka']['charge']})\n• Outside: {DELIVERY_POLICIES['outside']['time']} (৳{DELIVERY_POLICIES['outside']['charge']})\n• Free shipping on orders above ৳{DELIVERY_POLICIES['dhaka']['free_above']}\n\nThank you for choosing Nongor! 💚"
    
    reply_markup = get_back_button()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def user_contact(update: Update, context):
    text = f"📱 **CONTACT US**\n═══════════════════════════════\n\n📞 **Phone/WhatsApp**\n{CONTACT_INFO['whatsapp']}\n\n📧 **Email**\n{CONTACT_INFO['email']}\n\n🌐 **Website**\n{CONTACT_INFO['website']}\n\n🕐 **Business Hours**\n{BUSINESS_HOURS['weekdays']['days']}: {BUSINESS_HOURS['weekdays']['hours']}\n\n**Response Times:**\n• WhatsApp: {BUSINESS_HOURS['response_times']['whatsapp']} ⚡\n• Email: {BUSINESS_HOURS['response_times']['email']}"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())

async def user_support(update: Update, context):
    await user_contact(update, context)

# Message Processing
async def handle_message(update: Update, context):
    session = get_session(update.effective_user.id)
    text = update.message.text
    
    if session.state == "waiting_tracking":
        await process_tracking(update, text)
    else:
        await handle_ai_chat(update, context, text)

async def process_tracking(update: Update, text: str):
    await update.message.reply_text("🔍 Searching for order...")
    
    # Reset state
    session = get_session(update.effective_user.id)
    session.state = "menu"
    
    order = None
    if re.match(r'01[3-9]\d{8}', text):
        order = await db.get_order_by_phone(text)
    else:
        order_id_match = re.search(r'\d+', text)
        if order_id_match: 
            order = await db.get_order_by_id(int(order_id_match.group()))
    
    if order:
        resp = f"📦 **Order Found!**\nID: #{order.get('id', 'N/A')}\nStatus: {order.get('status', 'unknown').upper()}\nTotal: ৳{order.get('total', 0):,.0f}"
    else:
        resp = "❌ No order found. Please check the details and try again."
    
    await update.message.reply_text(resp, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())

from system_prompt import SYSTEM_PROMPT_TEMPLATE

# ... (Global imports remain same)

async def handle_ai_chat(update: Update, context, message: str):
    if not ai_initialized:
        await update.message.reply_text("⚠️ AI features are currently disabled.")
        return
    
    try:
        # 1. Prepare Context (Tools/Data)
        ctx = await db.get_products_for_context()
        policies = f"Delivery: Dhaka {DELIVERY_POLICIES['dhaka']['time']}, Outside {DELIVERY_POLICIES['outside']['time']}. Free ship > {DELIVERY_POLICIES['dhaka']['free_above']}."
        
        # 2. Inject Dynamic Values into System Prompt
        admin_ids_str = ", ".join(map(str, ADMIN_USER_IDS))
        system_instruction = SYSTEM_PROMPT_TEMPLATE.replace("{PUT_ADMIN_TELEGRAM_USER_IDS_HERE}", admin_ids_str)
        
        # 3. Construct User Prompt with Context Data
        # We append the "Data Sources" to the user message so Gemini treats them as retrieved info.
        full_user_prompt = f"""
CONTEXT DATA (Use this to answer):
----------------------------------
POLICIES:
{policies}

CURRENT PRODUCT INVENTORY:
{ctx}
----------------------------------

USER MESSAGE:
{message}
"""
        
        # 4. Generate Response
        # Note: system_instruction is passed to GenerativeModel constructor if supported, 
        # or we rely on 'role: system' in prompt history.
        # or we rely on 'role: system' in prompt history.
        # For 'google-generativeai', we can use system_instruction in GenerativeModel.
        # Using 'gemini-1.5-flash' should work, but trying 'gemini-1.5-flash-latest' to be safe.
        model = genai.GenerativeModel('gemini-flash-latest', system_instruction=system_instruction)
        response = model.generate_content(full_user_prompt)
        reply = response.text
        
        try:
            await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        except BadRequest:
            await update.message.reply_text(reply)
            
    except Exception as e:
        logger.error(f"AI Error: {e}")
        await update.message.reply_text("⚠️ Error generating response. Please try again.")

async def button_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    session = get_session(user.id, user.username, user.first_name)
    data = query.data
    
    dispatch_map = {
        "admin_dashboard": admin_dashboard,
        "admin_orders": admin_orders,
        "admin_sales": admin_sales,
        "admin_inventory": admin_inventory,
        "admin_export": admin_export,
        "admin_chart": admin_chart,
        "user_products": user_products,
        "user_track_order": user_track_order,
        "user_about": user_about,
        "user_contact": user_contact,
    }
    
    if data in dispatch_map:
        await dispatch_map[data](update, context)
    elif data == "user_ai_chat":
        session.state = "ai_chat"
        await query.edit_message_text(
            "💬 **AI Assistant Active**\n\nAsk me anything about our products!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
    elif data == "back_menu":
        if session.role == "admin":
            text = f"👋 Welcome back, Admin **{user.first_name}**!\nChoose an option:"
            reply_markup = get_admin_menu()
        else:
            text = f"👋 Salam, **{user.first_name}**! Welcome to Nongor Premium.\nHow can I help you today?"
            reply_markup = get_user_menu()
        
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        except BadRequest:
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# ===============================================
# MAIN EXECUTION
# ===============================================

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is missing!")
        return

    # We use post_init to start our own asyncio tasks
    async def post_init(app: Application):
        await db.connect()
        asyncio.create_task(monitor_website(app))
        asyncio.create_task(daily_report_scheduler(app))
        asyncio.create_task(poll_orders_loop(app))
        
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("help", help_command))
    
    # Admin
    application.add_handler(CommandHandler("dashboard", admin_dashboard))
    application.add_handler(CommandHandler("orders", admin_orders))
    application.add_handler(CommandHandler("sales", admin_sales))
    application.add_handler(CommandHandler("inventory", admin_inventory))
    
    # User Shortcuts
    application.add_handler(CommandHandler("track", user_track_order))
    application.add_handler(CommandHandler("products", user_products))
    application.add_handler(CommandHandler("about", user_about))
    application.add_handler(CommandHandler("contact", user_contact))
    application.add_handler(CommandHandler("support", user_support))
    
    # Callback & Message
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot started in POLLING mode...")
    
    # Fix for Python 3.10+ "There is no current event loop"
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    application.run_polling()

# ===============================================
# HELPER FUNCTIONS
# ===============================================

async def generate_sales_chart():
    """Generate a sales chart image."""
    try:
        data = await db.get_daily_sales_stats(days=7)
        if not data: return None
        
        dates = [row['date'] for row in data]
        revenues = [row['revenue'] for row in data]
        
        plt.figure(figsize=(10, 6))
        plt.plot(dates, revenues, marker='o', linestyle='-', color='#2ecc71')
        plt.title('Sales Last 7 Days')
        plt.xlabel('Date')
        plt.ylabel('Revenue (BDT)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        logger.error(f"Chart generation error: {e}")
        return None

async def generate_orders_csv():
    """Generate CSV file of all orders."""
    try:
        orders = await db.get_all_orders()
        if not orders: return None
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Order ID', 'Customer', 'Phone', 'Product', 'Total', 'Status', 'Date'])
        
        for o in orders:
            writer.writerow([
                o['order_id'], 
                o['customer_name'], 
                o['phone'], 
                o['product_name'], 
                o['total'], 
                o['status'], 
                o['created_at']
            ])
            
        return io.BytesIO(output.getvalue().encode('utf-8'))
    except Exception as e:
        logger.error(f"CSV generation error: {e}")
        return None

# ===============================================
# BACKGROUND TASKS
# ===============================================

async def monitor_website(app: Application):
    """Background task to check website health every 5 minutes."""
    import httpx
    url = CONTACT_INFO['website']
    logger.info(f"Starting Website Monitor for {url}...")
    
    while True:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10)
                if resp.status_code >= 400:
                    msg = f"🚨 *WEBSITE ALERT!*\n\nURL: {url}\nStatus: {resp.status_code}\n\nAction required!"
                    for admin_id in ADMIN_USER_IDS:
                        try:
                            await app.bot.send_message(chat_id=admin_id, text=msg, parse_mode=ParseMode.MARKDOWN)
                        except Exception as e:
                            logger.error(f"Failed to send alert to {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Monitor Error: {e}")
            # Optional: Notify admin of monitor failure? Maybe too noisy.
            
        await asyncio.sleep(300) # 5 minutes

async def daily_report_scheduler(app: Application):
    """Background task to send daily reports at 9:00 PM BD Time (UTC+6)."""
    from datetime import timedelta, timezone
    
    logger.info("Starting Daily Report Scheduler...")
    
    # BD Timezone = UTC+6
    bd_tz = timezone(timedelta(hours=6))
    
    while True:
        now = datetime.now(bd_tz)
        
        # Target: 09:00 PM (21:00)
        # Check if it's 21:00:xx
        if now.hour == 21 and now.minute == 0:
            await send_daily_report(app)
            await asyncio.sleep(61) # Sleep to avoid duplicate sends
        else:
            # Sleep 30 seconds and check again
            await asyncio.sleep(30)

async def send_daily_report(app: Application):
    """Generates and sends the daily report."""
    try:
        today = await db.get_today_stats()
        weekly = await db.get_weekly_stats()
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        report_text = (
            f"📊 *DAILY BUSINESS REPORT* ({date_str})\n"
            "═══════════════════════════════\n\n"
            f"*KPIs:*\n📦 Orders: {today.get('order_count', 0)}\n💰 Revenue: ৳{today.get('total_revenue', 0):,.2f}\n\n"
            f"*WEEKLY:*\n📦 Orders: {weekly.get('order_count', 0)}\n💰 Revenue: ৳{weekly.get('total_revenue', 0):,.2f}"
        )
        
        for admin_id in ADMIN_USER_IDS:
            try:
                await app.bot.send_message(chat_id=admin_id, text=report_text, parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                logger.error(f"Failed to send report to {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Report Generation Error: {e}")

async def poll_orders_loop(app: Application):
    """Check for new orders every minute."""
    logger.info("Starting Order Polling Loop...")
    last_id = await db.get_latest_order_id()
    
    while True:
        try:
            # Check for orders > last_id
            # optimize: fetch only IDs > last_id
            # For now, we can reuse get_recent_orders but logic needs to be precise
            # Let's add specific query logic here or use db method
            # We need a method to fetch orders > ID. 
            # Adding ad-hoc query here for simplicity as db class update was already done
            query = "SELECT * FROM orders WHERE id > $1 ORDER BY id ASC"
            new_orders = await db.fetch_all(query, [last_id])
            
            for order in new_orders:
                last_id = order['id']
                msg = (
                    f"🎉 *NEW ORDER RECEIVED!*\n"
                    f"🆔 Order #{order['id']}\n"
                    f"👤 {order['customer_name']}\n"
                    f"💰 ৳{order['total']:,.0f}\n"
                    f"📦 {order['product_name']}"
                )
                for admin_id in ADMIN_USER_IDS:
                    try:
                        await app.bot.send_message(chat_id=admin_id, text=msg, parse_mode=ParseMode.MARKDOWN)
                    except Exception as e:
                        logger.error(f"Failed to notify {admin_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Polling Error: {e}")
            
        await asyncio.sleep(60)

async def admin_export(update: Update, context):
    if update.effective_user.id not in ADMIN_USER_IDS: return
    
    message = update.message if update.message else update.callback_query.message
    msg = await message.reply_text("⏳ Generating CSV export...")
    
    csv_file = await generate_orders_csv()
    
    if csv_file:
        date_str = datetime.now().strftime('%Y-%m-%d')
        await message.reply_document(
            document=csv_file,
            filename=f"nongor_orders_{date_str}.csv",
            caption=f"📦 Order Export ({date_str})"
        )
        await msg.delete()
    else:
        await msg.edit_text("❌ Failed to generate export.")

async def admin_chart(update: Update, context):
    if update.effective_user.id not in ADMIN_USER_IDS: return
    
    message = update.message if update.message else update.callback_query.message
    msg = await message.reply_text("⏳ Generating Sales Chart...")
    
    chart_img = await generate_sales_chart()
    
    if chart_img:
        await message.reply_photo(photo=chart_img, caption="📊 **Weekly Sales Trend**", parse_mode=ParseMode.MARKDOWN)
        await msg.delete()
    else:
        await msg.edit_text("❌ Failed to generate chart.")

if __name__ == "__main__":
    main()
