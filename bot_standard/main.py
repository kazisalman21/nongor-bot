
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

# Import Database (Enhanced Version)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import Database

# 3rd Party Imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
import csv
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Optional: AI
try:
    import google.generativeai as genai
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    logger.warning("google-generativeai not installed. AI features disabled.")

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

if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN is missing in .env!")
    sys.exit(1)

# Initialize Database
db = Database(DATABASE_URL)

# Initialize AI
ai_initialized = False
if AI_AVAILABLE and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        ai_model = genai.GenerativeModel('gemini-2.5-flash')
        ai_initialized = True
        logger.info("AI initialized successfully with model gemini-2.5-flash")
    except Exception as e:
        logger.error(f"AI initialization failed: {e}")

CONTACT_INFO = {
    'website': 'https://nongor-brand.vercel.app',
    'facebook': 'https://www.facebook.com/profile.php?id=61582283911710',
    'messenger': 'https://m.me/857107060814707',
    'email': 'nongorr.anika@gmail.com',
    # Phone/Whatsapp removed as they are not on the website
    'phone': None, 
    'whatsapp': None
}

BUSINESS_HOURS = {
    "weekdays": {"days": "Everyday", "hours": "10:00 AM - 10:00 PM"},
    "friday": {"days": "Friday", "hours": "Open"},
    "response_times": {"messenger": "~2 minutes", "email": "Within 24 hours"}
}

import httpx
from telegram.ext import JobQueue

DELIVERY_POLICIES = {
    "dhaka": {"time": "2-3 days", "charge": 70, "free_above": 1000},
    "outside": {"time": "3-5 days", "charge": 130, "free_above": 2000}
}

WEBSITE_URL = os.getenv("WEBSITE_URL", "https://nongor-brand.vercel.app")


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
        self.temp_data = {}

user_sessions = {}

def get_session(user_id, username=None, first_name=None):
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id, username, first_name)
    session = user_sessions[user_id]
    session.last_activity = datetime.now()
    return session

# Load Knowledge Base
try:
    with open('bot_standard/knowledge_base.md', 'r', encoding='utf-8') as f:
        KNOWLEDGE_BASE = f.read()
    logger.info("Knowledge base loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load knowledge base: {e}")
    KNOWLEDGE_BASE = ""

AI_CUSTOMER_PROMPT = f"""You are 'Nongor AI', the Lead Sales Manager for Nongor Brand.
Your goal is to DRIVE SALES while maintaining 100% adherence to company policies.

BACKGROUND INFO (STRICT RULES):
{{KNOWLEDGE_BASE}}

SALES STRATEGY:
1. **Consultative Selling**: Don't just answer; ask questions to understand their needs. (e.g., "Are you buying this for a special occasion?")
2. **Urgency**: If a product is good, mention high demand. (e.g., "This design is our bestseller right now!")
3. **Closing**: Always end with a Call to Action. (e.g., "Shall I confirm this order for you?")
4. **Value Proposition**: Focus on the premium quality and fast delivery (Inside Dhaka: 2-3 days).

GUIDELINES:
1. **Tone**: Warm, energetic, and professional. Use emojis to build rapport. 🤝✨
2. **Policy Adherence**: NEVER bend the rules on Shipping charges or Return limits (3 days). If asked, politely cite the policy.
3. **Language**: Mirror the customer's language (Bengali/English).
4. **Escalation**: If you cannot help, guide them to the "Contact" button.
"""

AI_ADMIN_PROMPT = """You are the 'Senior Business Manager' for Nongor Brand.
Your goal is to act as a strategic advisor to the owner, analyzing data to find faults, opportunities, and growth trends.

CAPABILITIES:
1. **Revenue Analysis**: Compare Daily vs Weekly vs Monthly performance.
2. **Inventory Health**: Identify dead stock (low sales) and fast-movers (high sales).
3. **Fault Finding**: Point out if conversion rates seem low or if specific products are underperforming.
4. **Strategic Advice**: Suggest marketing for slow days or restocking for popular items.

GUIDELINES:
1. **Tone**: Executive, critical, and data-driven. Don't just report numbers; interprete them.
2. **Proactive**: If you see low stock on a top seller, WARN the admin immediately.
3. **Format**: Use bullet points. Bold key metrics (e.g., **৳50,000**).
4. **Context**: You have access to full sales history and inventory. Use it to back up your claims.
"""

# ===============================================
# KEYBOARDS
# ===============================================

def get_admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard"),
         InlineKeyboardButton("📈 Analytics", callback_data="admin_analytics")],
        [InlineKeyboardButton("📦 Orders", callback_data="admin_orders"),
         InlineKeyboardButton("🔍 Search Order", callback_data="admin_search")],
        [InlineKeyboardButton("🛍️ Products", callback_data="admin_products"),
         InlineKeyboardButton("🎟️ Coupons", callback_data="admin_coupons")],
        [InlineKeyboardButton("📤 Export CSV", callback_data="admin_export"),
         InlineKeyboardButton("📊 Sales Chart", callback_data="admin_chart")],
        [InlineKeyboardButton("🤖 AI Assistant", callback_data="admin_ai_chat") if ai_initialized else None],
        [InlineKeyboardButton("◀️ Refresh", callback_data="back_menu")]
    ])

def get_user_menu():
    buttons = [
        [InlineKeyboardButton("📦 Track Order", callback_data="user_track_order"),
         InlineKeyboardButton("🛍️ Products", callback_data="user_products")],
        [InlineKeyboardButton("ℹ️ About Us", callback_data="user_about"),
         InlineKeyboardButton("📱 Contact", callback_data="user_contact")],
        [InlineKeyboardButton("📜 Policies", callback_data="user_policies")]
    ]
    
    if ai_initialized:
        buttons.insert(0, [InlineKeyboardButton("🤖 Chat with AI", callback_data="user_ai_chat")])
    
    return InlineKeyboardMarkup(buttons)

def get_back_button(callback_data="back_menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back to Menu", callback_data=callback_data)]])

def get_order_filter_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 All Orders", callback_data="filter_all"),
         InlineKeyboardButton("⏳ Pending", callback_data="filter_pending")],
        [InlineKeyboardButton("✅ Delivered", callback_data="filter_delivered"),
         InlineKeyboardButton("❌ Cancelled", callback_data="filter_cancelled")],
        [InlineKeyboardButton("◀️ Back", callback_data="admin_orders")]
    ])

# ===============================================
# COMMAND HANDLERS
# ===============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = get_session(user.id, user.username, user.first_name)
    session.state = "menu"
    
    await db.save_user(user.id, user.username, user.first_name)
    
    if session.role == "admin":
        text = (
            f"👋 **Hello! I am Eikta**\n"
            f"🤖 *Your Personal Assistant for Nongor*\n\n"
            f"👤 **{user.first_name}** (`@{user.username}`)\n"
            f"🆔 `{user.id}`\n\n"
            f"🛠 **Admin Control Panel**\n"
            f"Select an action below to manage your store:"
        )
        reply_markup = get_admin_menu()
    else:
        text = (
            f"👋 **Hello! I am Eikta**\n"
            f"🤖 *Your Personal Shopping Assistant*\n\n"
            f"Welcome to **Nongor**! 🌸\n"
            f"I'm here to help you find the perfect outfit.\n\n"
            f"👤 **{user.first_name}**\n"
            f"🆔 `{user.id}`\n\n"
            f"🛍 **How can I help you today?**"
        )
        reply_markup = get_user_menu()
    
    try:
        if update.message:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    except BadRequest:
        if update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_USER_IDS
    
    if is_admin:
        text = """📚 **ADMIN COMMANDS**

/start - Main menu
/dashboard - Quick stats
/orders - Recent orders
/export - Export CSV
/search - Search orders
/products - Product list
/help - This help message
"""
    else:
        text = """📚 **AVAILABLE COMMANDS**

/start - Main menu
/track - Track your order
/products - Browse products
/about - About Nongor
/contact - Contact us
/help - This help message
"""
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ===============================================
# ADMIN HANDLERS
# ===============================================

async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS: 
        return
    
    try:
        today = await db.get_today_stats()
        weekly = await db.get_weekly_stats()
        monthly = await db.get_monthly_stats()
        users = await db.get_user_stats()
        pending = await db.get_pending_orders_count()
        low_stock = await db.get_low_stock_products(threshold=10)
        
        text = f"""📊 **BUSINESS DASHBOARD**
━━━━━━━━━━━━━━━━━━━━━━

📅 **TODAY:**
📦 Orders: {today.get('order_count', 0)}
💰 Revenue: ৳{today.get('total_revenue', 0):,.2f}
📊 Avg Value: ৳{today.get('avg_order_value', 0):,.2f}

📅 **THIS WEEK:**
📦 Orders: {weekly.get('order_count', 0)}
💰 Revenue: ৳{weekly.get('total_revenue', 0):,.2f}
📊 Avg Value: ৳{weekly.get('avg_order_value', 0):,.2f}

📅 **THIS MONTH:**
📦 Orders: {monthly.get('order_count', 0)}
💰 Revenue: ৳{monthly.get('total_revenue', 0):,.2f}

👥 **USERS:**
Total: {users.get('total_users', 0)}
Active (7d): {users.get('active_users', 0)}

⚠️ **ALERTS:**
⏳ Pending Orders: {pending}
📦 Low Stock Items: {len(low_stock)}
"""
        
        reply_markup = get_back_button()
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        error_text = "❌ Error loading dashboard. Please try again."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)

async def admin_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS: 
        return
    
    try:
        status_breakdown = await db.get_status_breakdown()
        payment_stats = await db.get_payment_method_stats()
        delivery_breakdown = await db.get_delivery_status_breakdown()
        
        text = "📊 **ADVANCED ANALYTICS** (Last 30 Days)\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Order Status
        text += "📋 **Order Status:**\n"
        for stat in status_breakdown:
            text += f"• {stat['status']}: {stat['count']} orders (৳{stat['revenue']:,.0f})\n"
        
        text += "\n💳 **Payment Methods:**\n"
        for method in payment_stats:
            text += f"• {method['payment_method']}: {method['count']} orders (৳{method['revenue']:,.0f})\n"
        
        text += "\n🚚 **Delivery Status:**\n"
        for delivery in delivery_breakdown:
            text += f"• {delivery['delivery_status']}: {delivery['count']} orders\n"
        
        reply_markup = get_back_button()
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        await send_error_message(update, "loading analytics")

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS: 
        return
    
    try:
        orders = await db.get_recent_orders(limit=10)
        
        if not orders:
            text = "📦 **RECENT ORDERS**\n\nNo orders found."
        else:
            text = "📦 **RECENT ORDERS**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for o in orders:
                # Fixed: Use total_price instead of total
                total = o.get('total_price', 0) or 0
                status_emoji = get_status_emoji(o.get('status'))
                text += f"{status_emoji} **{o.get('order_id', 'N/A')}**\n"
                text += f"👤 {o.get('customer_name', 'Unknown')}\n"
                text += f"📱 {o.get('phone', 'N/A')}\n"
                text += f"💰 ৳{total:,.0f}\n"
                text += f"📊 {o.get('delivery_status', o.get('status', 'N/A'))}\n"
                text += "─────────────────\n"
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search Order", callback_data="admin_search"),
             InlineKeyboardButton("🔄 Filter", callback_data="admin_filter")],
            [InlineKeyboardButton("◀️ Back", callback_data="back_menu")]
        ])
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Orders error: {e}")
        await send_error_message(update, "loading orders")

async def admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS: 
        return
    
    try:
        products = await db.get_all_products(active_only=True)
        low_stock = await db.get_low_stock_products(threshold=10)
        
        text = f"🛍️ **PRODUCT INVENTORY**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"📊 Total Active: {len(products)}\n"
        text += f"⚠️ Low Stock: {len(low_stock)}\n\n"
        
        if low_stock:
            text += "**⚠️ Low Stock Alert:**\n"
            for p in low_stock[:5]:
                text += f"• {p['name']}: {p['stock_quantity']} left\n"
            text += "\n"
        
        text += "**All Products:**\n"
        # Show all products (limit to 10 for now to avoid message limit)
        display_products = products[:10]
        for p in display_products:
            stock_emoji = "✅" if p['stock_quantity'] > 10 else "⚠️"
            featured_star = "⭐" if p.get('is_featured') else ""
            text += f"{stock_emoji} {p['name']} {featured_star}\n"
            text += f"   ৳{p['price']:,.0f} • Stock: {p['stock_quantity']}\n"
        
        reply_markup = get_back_button()
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Products error: {e}")
        await send_error_message(update, "loading products")

async def admin_coupons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS: 
        return
    
    try:
        # Fetch ALL coupons (active and inactive)
        coupons = await db.get_all_coupons(active_only=False)
        
        if not coupons:
            text = "🎟️ **COUPON MANAGEMENT**\n\nNo coupons found."
        else:
            text = "🎟️ **COUPON MANAGEMENT**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for c in coupons:
                status_emoji = "✅" if c.get('is_active', True) else "❌"
                discount_text = f"{c['discount_value']}%" if c['discount_type'] == 'percentage' else f"৳{c['discount_value']}"
                usage_text = f"{c['used_count']}/{c['usage_limit']}" if c['usage_limit'] else f"{c['used_count']} used"
                
                text += f"{status_emoji} **{c['code']}**\n"
                text += f"💰 {discount_text} off\n"
                text += f"📊 {usage_text}\n"
                if c['min_order_amount']:
                    text += f"📦 Min: ৳{c['min_order_amount']}\n"
                if c['valid_until']:
                    text += f"⏰ Until: {c['valid_until'].strftime('%Y-%m-%d')}\n"
                text += "─────────────────\n"
        
        reply_markup = get_back_button()
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Coupons error: {e}")
        await send_error_message(update, "loading coupons")

async def admin_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS:
        return
    
    session = get_session(update.effective_user.id)
    session.state = "waiting_search"
    
    text = "🔍 **SEARCH ORDERS**\n\nEnter order ID, customer name, phone, or email:"
    reply_markup = get_back_button()
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def admin_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS:
        return
    
    reply_markup = get_order_filter_menu()
    text = "🔄 **FILTER ORDERS**\n\nChoose a status to filter:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def handle_filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id not in ADMIN_USER_IDS:
        return
    
    filter_type = query.data.replace("filter_", "")
    
    try:
        if filter_type == "all":
            orders = await db.get_recent_orders(limit=20)
            title = "ALL ORDERS"
        else:
            status_map = {
                "pending": "Pending",
                "delivered": "Delivered",
                "cancelled": "Cancelled"
            }
            status = status_map.get(filter_type, filter_type.capitalize())
            orders = await db.get_orders_by_status(status, limit=20)
            title = f"{status.upper()} ORDERS"
        
        if not orders:
            text = f"📦 **{title}**\n\nNo orders found."
        else:
            text = f"📦 **{title}**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for o in orders:
                total = o.get('total_price', 0) or 0
                status_emoji = get_status_emoji(o.get('status'))
                text += f"{status_emoji} **{o.get('order_id', 'N/A')}** - ৳{total:,.0f}\n"
                text += f"👤 {o.get('customer_name', 'Unknown')}\n"
                text += "─────────────────\n"
        
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="admin_orders")]])
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Filter error: {e}")
        await query.edit_message_text("❌ Error filtering orders.")

async def admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS: 
        return
    
    message = update.message if update.message else update.callback_query.message
    msg = await message.reply_text("⏳ Generating CSV export...")
    
    try:
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
            await msg.edit_text("❌ No orders to export.")
    except Exception as e:
        logger.error(f"Export error: {e}")
        await msg.edit_text("❌ Failed to generate export.")

async def admin_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS: 
        return
    
    message = update.message if update.message else update.callback_query.message
    msg = await message.reply_text("⏳ Generating sales chart...")
    
    try:
        chart_img = await generate_sales_chart()
        
        if chart_img:
            await message.reply_photo(
                photo=chart_img, 
                caption="📊 **Weekly Sales Trend**", 
                parse_mode=ParseMode.MARKDOWN
            )
            await msg.delete()
        else:
            await msg.edit_text("❌ Not enough data to generate chart.")
    except Exception as e:
        logger.error(f"Chart error: {e}")
        await msg.edit_text("❌ Failed to generate chart.")

# ===============================================
# USER HANDLERS
# ===============================================

async def user_track_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_user.id)
    session.state = "waiting_order_id"
    
    text = """📦 **TRACK YOUR ORDER**

Please enter your Order ID
(e.g., #NG-63497)"""
    
    reply_markup = get_back_button()
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def user_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Changed to get ALL active products instead of just featured
        products = await db.get_all_products(active_only=True)
        
        text = "🛍️ **OUR PRODUCTS**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if products:
            for p in products:
                stock_text = "✅ In Stock" if p['stock_quantity'] > 0 else "❌ Out of Stock"
                text += f"**{p['name']}**\n"
                text += f"💰 ৳{p['price']:,.0f} • {stock_text}\n"
                if p.get('description'):
                    desc = p['description'][:60] + "..." if len(p['description']) > 60 else p['description']
                    text += f"📝 {desc}\n"
                text += "─────────────────\n"
        else:
            text += "No products available at the moment.\n"
        
        text += f"\n🌐 Visit our website:\n{CONTACT_INFO['website']}"
        
        reply_markup = get_back_button()
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Products error: {e}")
        await send_error_message(update, "loading products")

async def user_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """ℹ️ **ABOUT NONGOR PREMIUM**

🌸 Nongor is your destination for premium Bengali cultural fashion and lifestyle products.

**What We Offer:**
• Traditional and modern Bengali clothing
• Handcrafted accessories
• Cultural merchandise
• Custom designs

**Why Choose Us:**
✅ Authentic Bengali designs
✅ High-quality materials
✅ Fast delivery across Bangladesh
✅ Easy returns & exchanges
✅ Secure payment options

🌐 Website: {}
📱 Follow us: {}
""".format(CONTACT_INFO['website'], CONTACT_INFO['facebook'])
    
    reply_markup = get_back_button()
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def user_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"""📱 **CONTACT US**

**Get in Touch:**

📞 Phone: {CONTACT_INFO['phone']}
💬 WhatsApp: {CONTACT_INFO['whatsapp']}
📧 Email: {CONTACT_INFO['email']}
🌐 Website: {CONTACT_INFO['website']}
📘 Facebook: {CONTACT_INFO['facebook']}

**Business Hours:**
{BUSINESS_HOURS['weekdays']['days']}: {BUSINESS_HOURS['weekdays']['hours']}
{BUSINESS_HOURS['friday']['days']}: {BUSINESS_HOURS['friday']['hours']}

**Response Times:**
WhatsApp: {BUSINESS_HOURS['response_times']['whatsapp']}
Email: {BUSINESS_HOURS['response_times']['email']}
"""
    
    reply_markup = get_back_button()
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def user_policies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"""📜 **POLICIES & INFORMATION**

**🚚 Shipping:**
• Dhaka: {DELIVERY_POLICIES['dhaka']['time']} (৳{DELIVERY_POLICIES['dhaka']['charge']})
• Outside Dhaka: {DELIVERY_POLICIES['outside']['time']} (৳{DELIVERY_POLICIES['outside']['charge']})
• Free shipping on orders above ৳{DELIVERY_POLICIES['dhaka']['free_above']} (Dhaka)

**💳 Payment:**
• Cash on Delivery (COD)
• bKash/Nagad
• Bank Transfer

**🔄 Returns:**
• 7-day return policy
• Items must be unused and in original packaging
• Return shipping charges may apply

**🔒 Privacy:**
• Your information is secure
• We don't share data with third parties
• See full policy on our website

For detailed policies, visit:
{CONTACT_INFO['website']}/policies
"""
    
    reply_markup = get_back_button()
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# ===============================================
# AI CHAT HANDLERS
# ===============================================

async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ai_initialized:
        text = "🤖 AI Assistant is not available at the moment."
        reply_markup = get_back_button()
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        return
    
    session = get_session(update.effective_user.id)
    session.state = "ai_chat"
    
    if session.role == "admin":
        text = """🤖 **ADMIN AI ASSISTANT**

I can help you with:
• Business insights and analytics
• Product recommendations
• Order management tips
• Customer service guidance

Ask me anything about your business!

Type your question or /menu to return."""
    else:
        text = """🤖 **SHOPPING ASSISTANT**

Hi! I'm your Nongor shopping assistant.

I can help you with:
• Product recommendations
• Order questions
• Sizing and fit
• General inquiries

What would you like to know?

Type your question or /menu to return."""
    
    reply_markup = get_back_button()
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# ===============================================
# MESSAGE HANDLER
# ===============================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = get_session(user_id)
    user_text = update.message.text.strip()
    
    # Handle order ID input
    if session.state == "waiting_order_id":
        await handle_order_tracking(update, context, user_text)
        return
    
    # Handle search input
    if session.state == "waiting_search":
        await handle_search_query(update, context, user_text)
        return
    
    # Handle AI chat
    if session.state == "ai_chat":
        await handle_ai_message(update, context, user_text)
        return
    
    # Default: Show menu
    await start(update, context)

async def handle_order_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id):
    try:
        # Try to find order by order_id string
        order = await db.get_order_by_order_id(order_id)
        
        # If not found, try numeric ID
        if not order and order_id.replace('#', '').replace('NG-', '').replace('ng-', '').isdigit():
            numeric_id = int(order_id.replace('#', '').replace('NG-', '').replace('ng-', ''))
            order = await db.get_order_by_id(numeric_id)
        
        if not order:
            text = f"❌ Order **{order_id}** not found.\n\nPlease check your order ID and try again."
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())
            return
        
        # Build order details
        total = order.get('total_price', 0) or 0
        status_emoji = get_status_emoji(order.get('status'))
        
        text = f"""📦 **ORDER DETAILS**
━━━━━━━━━━━━━━━━━━━━━━

**Order ID:** {order.get('order_id', 'N/A')}
**Status:** {status_emoji} {order.get('delivery_status', order.get('status', 'N/A'))}

**Customer:** {order.get('customer_name', 'N/A')}
**Phone:** {order.get('phone', 'N/A')}
**Address:** {order.get('address', 'N/A')}

**Product:** {order.get('product_name', 'N/A')}
**Quantity:** {order.get('quantity', 1)}
**Total:** ৳{total:,.2f}

**Payment Method:** {order.get('payment_method', 'N/A')}
**Payment Status:** {order.get('payment_status', 'N/A')}
"""
        
        if order.get('coupon_code'):
            text += f"**Coupon:** {order['coupon_code']} (-৳{order.get('discount_amount', 0)})\n"
        
        if order.get('tracking_token'):
            text += f"\n**Tracking:** {order['tracking_token'][:20]}...\n"
        
        text += f"\n**Ordered:** {order.get('created_at').strftime('%Y-%m-%d %H:%M') if order.get('created_at') else 'N/A'}"
        
        if order.get('delivery_date'):
            text += f"\n**Expected Delivery:** {order['delivery_date']}"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())
        
    except Exception as e:
        logger.error(f"Order tracking error: {e}")
        await update.message.reply_text("❌ Error retrieving order details.", reply_markup=get_back_button())
    
    session = get_session(update.effective_user.id)
    session.state = "menu"

async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE, search_term):
    if update.effective_user.id not in ADMIN_USER_IDS:
        return
    
    try:
        results = await db.search_orders(search_term)
        
        if not results:
            text = f"🔍 **SEARCH RESULTS**\n\nNo orders found for: **{search_term}**"
        else:
            text = f"🔍 **SEARCH RESULTS** ({len(results)} found)\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for o in results[:10]:
                total = o.get('total_price', 0) or 0
                status_emoji = get_status_emoji(o.get('status'))
                text += f"{status_emoji} **{o.get('order_id', 'N/A')}**\n"
                text += f"👤 {o.get('customer_name', 'Unknown')} • 📱 {o.get('phone', 'N/A')}\n"
                text += f"💰 ৳{total:,.0f} • {o.get('delivery_status', o.get('status', 'N/A'))}\n"
                text += "─────────────────\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("❌ Error searching orders.", reply_markup=get_back_button())
    
    session = get_session(update.effective_user.id)
    session.state = "menu"

async def handle_ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text):
    if not ai_initialized:
        await update.message.reply_text("🤖 AI is not available.")
        return
    
    session = get_session(update.effective_user.id)
    
    try:
        # Build context
        if session.role == "admin":
            # Fetch Advanced Business Data
            today_stats = await db.get_today_stats()
            weekly_stats = await db.get_weekly_stats()
            monthly_stats = await db.get_monthly_stats()
            top_products = await db.get_top_products(days=30, limit=5)
            low_stock = await db.get_inventory_alerts()
            cat_revenue = await db.get_revenue_by_category(days=30)
            
            # Format Top Products
            top_prod_text = "\n".join([f"- {p['product_name']}: ৳{p['revenue']:,.0f} ({p['order_count']} orders)" for p in top_products]) if top_products else "No sales data."
            
            # Format Low Stock
            low_stock_text = "\n".join([f"- {p['name']}: {p['stock_quantity']} left" for p in low_stock]) if low_stock else "Inventory looks healthy."

            # Format Category Performance
            cat_text = "\n".join([f"- {c['category_name']}: ৳{c['revenue']:,.0f}" for c in cat_revenue]) if cat_revenue else "No category data."

            prompt = f"""{AI_ADMIN_PROMPT}

📊 **EXECUTIVE DASHBOARD**:

**1. Revenue Snapshot**:
- Today: ৳{today_stats.get('total_revenue', 0):,.0f} ({today_stats.get('order_count', 0)} orders)
- Last 7 Days: ৳{weekly_stats.get('total_revenue', 0):,.0f}
- Last 30 Days: ৳{monthly_stats.get('total_revenue', 0):,.0f}

**2. ⭐ Top Performers (30 Days)**:
{top_prod_text}

**3. ⚠️ Inventory Alerts**:
{low_stock_text}

**4. 📈 Category Analysis**:
{cat_text}

**Admin Query**: {user_text}

Provide a senior-level strategic analysis based on these numbers."""
        else:
            products_context = await db.get_products_for_context()
            
            prompt = f"""{AI_CUSTOMER_PROMPT}

PRODUCT CATALOG CONTEXT:
{products_context}

Customer Query: {user_text}

Response:"""
        
        response = ai_model.generate_content(prompt)
        ai_text = response.text
        
        # Limit response length
        if len(ai_text) > 800:
            ai_text = ai_text[:800] + "..."
        
        await update.message.reply_text(ai_text, reply_markup=get_back_button())
        
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        await update.message.reply_text("🤖 Sorry, I couldn't process that. Please try again.", reply_markup=get_back_button())

# ===============================================
# CALLBACK QUERY HANDLER
# ===============================================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    callback_map = {
        "back_menu": start,
        "admin_dashboard": admin_dashboard,
        "admin_analytics": admin_analytics,
        "admin_orders": admin_orders,
        "admin_products": admin_products,
        "admin_coupons": admin_coupons,
        "admin_search": admin_search,
        "admin_filter": admin_filter,
        "admin_export": admin_export,
        "admin_chart": admin_chart,
        "admin_ai_chat": handle_ai_chat,
        "user_track_order": user_track_order,
        "user_products": user_products,
        "user_about": user_about,
        "user_contact": user_contact,
        "user_policies": user_policies,
        "user_ai_chat": handle_ai_chat,
    }
    
    # Handle filter callbacks
    if query.data.startswith("filter_"):
        await handle_filter_callback(update, context)
        return
    
    handler = callback_map.get(query.data)
    if handler:
        await handler(update, context)
    else:
        await query.edit_message_text("❌ Unknown action")

# ===============================================
# HELPER FUNCTIONS
# ===============================================

def get_status_emoji(status):
    """Get emoji for order status"""
    emoji_map = {
        "Pending": "⏳",
        "Processing": "🔄",
        "Shipped": "🚚",
        "Delivered": "✅",
        "Cancelled": "❌",
        "Returned": "↩️"
    }
    return emoji_map.get(status, "📦")

async def send_error_message(update, action):
    """Send standardized error message"""
    text = f"❌ Error {action}. Please try again."
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text)
    else:
        await update.message.reply_text(text)

async def generate_sales_chart():
    """Generate a sales chart image."""
    try:
        data = await db.get_daily_sales_stats(days=7)
        if not data or len(data) < 2:
            return None
        
        dates = [row['date'] for row in data]
        revenues = [float(row['revenue']) for row in data]
        
        plt.figure(figsize=(10, 6))
        plt.plot(dates, revenues, marker='o', linestyle='-', color='#2ecc71', linewidth=2)
        plt.title('Sales Last 7 Days', fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Revenue (৳)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Add value labels
        for i, (date, rev) in enumerate(zip(dates, revenues)):
            plt.text(i, rev, f'৳{rev:,.0f}', ha='center', va='bottom')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
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
        if not orders:
            return None
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Order ID', 'Customer', 'Phone', 'Email', 'Product', 
            'Quantity', 'Total', 'Status', 'Delivery Status', 
            'Payment Method', 'Payment Status', 'Coupon', 'Discount', 'Date'
        ])
        
        # Data
        for o in orders:
            writer.writerow([
                o.get('order_id', ''),
                o.get('customer_name', ''),
                o.get('phone', ''),
                o.get('customer_email', ''),
                o.get('product_name', ''),
                o.get('quantity', 0),
                o.get('total_price', 0),
                o.get('status', ''),
                o.get('delivery_status', ''),
                o.get('payment_method', ''),
                o.get('payment_status', ''),
                o.get('coupon_code', ''),
                o.get('discount_amount', 0),
                o.get('created_at', '')
            ])
        
        return io.BytesIO(output.getvalue().encode('utf-8-sig'))  # UTF-8 with BOM for Excel
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
                    msg = f"🚨 **WEBSITE ALERT!**\n\nURL: {url}\nStatus: {resp.status_code}\n\nAction required!"
                    for admin_id in ADMIN_USER_IDS:
                        try:
                            await app.bot.send_message(chat_id=admin_id, text=msg, parse_mode=ParseMode.MARKDOWN)
                        except Exception as e:
                            logger.error(f"Failed to send alert to {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Monitor Error: {e}")
        
        await asyncio.sleep(300)  # 5 minutes

async def daily_report_scheduler(app: Application):
    """Background task to send daily reports at 9:00 PM BD Time (UTC+6)."""
    from datetime import timedelta, timezone
    
    logger.info("Starting Daily Report Scheduler...")
    bd_tz = timezone(timedelta(hours=6))
    
    while True:
        now = datetime.now(bd_tz)
        
        if now.hour == 21 and now.minute == 0:
            await send_daily_report(app)
            await asyncio.sleep(61)
        else:
            await asyncio.sleep(30)

async def send_daily_report(app: Application):
    """Generates and sends the daily report."""
    try:
        today = await db.get_today_stats()
        weekly = await db.get_weekly_stats()
        top_products = await db.get_top_products(days=1, limit=3)
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        report_text = f"""📊 **DAILY BUSINESS REPORT** ({date_str})
═══════════════════════════════

**TODAY'S PERFORMANCE:**
📦 Orders: {today.get('order_count', 0)}
💰 Revenue: ৳{today.get('total_revenue', 0):,.2f}
📊 Avg Order: ৳{today.get('avg_order_value', 0):,.2f}

**WEEKLY SUMMARY:**
📦 Orders: {weekly.get('order_count', 0)}
💰 Revenue: ৳{weekly.get('total_revenue', 0):,.2f}
"""
        
        if top_products:
            report_text += "\n**🏆 TOP PRODUCTS TODAY:**\n"
            for i, p in enumerate(top_products, 1):
                report_text += f"{i}. {p['product_name']}: ৳{p.get('revenue', 0):,.0f}\n"
        
        for admin_id in ADMIN_USER_IDS:
            try:
                await app.bot.send_message(chat_id=admin_id, text=report_text, parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                logger.error(f"Failed to send report to {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Report Generation Error: {e}")

async def poll_orders_loop(app: Application):
    """Check for new orders every minute and notify admins."""
    logger.info("Starting Order Polling Loop...")
    last_id = await db.get_latest_order_id()
    
    while True:
        try:
            query = """
                SELECT 
                    id, 
                    order_id, 
                    customer_name, 
                    phone, 
                    product_name, 
                    total_price, 
                    payment_method, 
                    coupon_code,
                    discount_amount,
                    created_at 
                FROM orders 
                WHERE id > $1 
                ORDER BY id ASC
            """
            new_orders = await db.fetch_all(query, [last_id])
            
            for order in new_orders:
                last_id = order['id']
                total = order.get('total_price', 0) or 0
                
                msg = f"""🎉 **NEW ORDER RECEIVED!**

🆔 Order: {order.get('order_id', f"#{order['id']}")}
👤 Customer: {order.get('customer_name', 'N/A')}
📱 Phone: {order.get('phone', 'N/A')}
💰 Total: ৳{total:,.2f}
📦 Product: {order.get('product_name', 'N/A')}
💳 Payment: {order.get('payment_method', 'N/A')}
"""
                
                if order.get('coupon_code'):
                    msg += f"🎟️ Coupon: {order['coupon_code']} (-৳{order.get('discount_amount', 0):,.0f})\n"
                
                msg += f"\n⏰ {order.get('created_at', datetime.now()).strftime('%Y-%m-%d %H:%M')}\n"
                
                for admin_id in ADMIN_USER_IDS:
                    try:
                        await app.bot.send_message(chat_id=admin_id, text=msg, parse_mode=ParseMode.MARKDOWN)
                    except Exception as e:
                        logger.error(f"Failed to notify {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Polling Error: {e}")
        
        await asyncio.sleep(60)  # Check every minute

async def monitor_website_job(context: ContextTypes.DEFAULT_TYPE):
    """Background job to check website status"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(WEBSITE_URL)
            status = response.status_code
            
            # If status is not 200, ALERT ADMINS
            if status != 200:
                for admin_id in ADMIN_USER_IDS:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=f"🚨 **CRITICAL ALERT**: Website is DOWN!\n\nStatus Code: {status}\nURL: {WEBSITE_URL}",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception:
                        pass
            else:
                # Optional: Log success silently
                logger.info(f"Website Monitor: {WEBSITE_URL} is UP (200 OK)")

    except Exception as e:
        logger.error(f"Website Monitor Error: {e}")
        # Notify admin of monitoring failure
        for admin_id in ADMIN_USER_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"⚠️ **Monitor Alert**: Could not reach website.\nError: {str(e)}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass


async def handle_monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to control monitoring"""
    if update.effective_user.id not in ADMIN_USER_IDS:
        return

    args = context.args
    if not args:
        # Check status NOW
        async with httpx.AsyncClient() as client:
            try:
                start = datetime.now()
                resp = await client.get(WEBSITE_URL)
                duration = (datetime.now() - start).total_seconds() * 1000
                status_emoji = "✅" if resp.status_code == 200 else "❌"
                
                await update.message.reply_text(
                    f"{status_emoji} **Website Status**\n"
                    f"URL: {WEBSITE_URL}\n"
                    f"Code: `{resp.status_code}`\n"
                    f"Latency: `{duration:.0f}ms`\n\n"
                    "Use `/monitor on` to enable auto-alerts.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Connection Failed: {e}")
        return

    action = args[0].lower()
    job_queue = context.job_queue
    
    if action == "on":
        # Check if already running
        current_jobs = job_queue.get_jobs_by_name("website_monitor")
        if current_jobs:
            await update.message.reply_text("✅ Monitoring is already active.")
            return
            
        # Add job: Check every 10 minutes (600 seconds)
        job_queue.run_repeating(monitor_website_job, interval=600, first=10, name="website_monitor")
        await update.message.reply_text("📡 **Monitoring ENABLED**. Checking every 10 minutes.")
        
    elif action == "off":
        current_jobs = job_queue.get_jobs_by_name("website_monitor")
        for job in current_jobs:
            job.schedule_removal()
        await update.message.reply_text("🔕 **Monitoring DISABLED**.")
    else:
        await update.message.reply_text("Usage: `/monitor` (check once), `/monitor on`, `/monitor off`")

# ===============================================
# MAIN
# ===============================================

async def post_init(application: Application):
    """Post-initialization hook to start background tasks."""
    logger.info("Starting background tasks...")
    asyncio.create_task(monitor_website(application))
    asyncio.create_task(daily_report_scheduler(application))
    asyncio.create_task(poll_orders_loop(application))
    logger.info("✅ Background tasks started.")

def main():
    """Start the bot."""
    logger.info("Starting Nongor Bot (Enhanced Version)...")
    
    # Build application with post_init hook
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("dashboard", admin_dashboard))
    application.add_handler(CommandHandler("orders", admin_orders))
    application.add_handler(CommandHandler("export", admin_export))
    application.add_handler(CommandHandler("search", admin_search))
    application.add_handler(CommandHandler("monitor", handle_monitor_command))
    application.add_handler(CommandHandler("products", user_products))
    application.add_handler(CommandHandler("track", user_track_order))
    application.add_handler(CommandHandler("about", user_about))
    application.add_handler(CommandHandler("contact", user_contact))
    
    # Callback and message handlers
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Bot configured successfully!")
    logger.info(f"👥 Admin User IDs: {ADMIN_USER_IDS}")
    logger.info(f"🤖 AI Enabled: {ai_initialized}")
    
    # Run bot
    application.run_polling()

if __name__ == "__main__":
    main()
