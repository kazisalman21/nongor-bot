"""
Nongor Bot V3 - Enhanced Telegram Bot
Dual-Mode: Admin Management + User Customer Service
"""

import os
import re
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode
from dotenv import load_dotenv

import google.generativeai as genai

from database_enhanced import get_database
from ai_context_builder import (
    get_full_ai_context, get_order_details, 
    format_order_details, search_products_for_ai,
    clear_context_cache
)
from config.business_config import (
    CONTACT_INFO, BUSINESS_HOURS, DELIVERY_POLICIES,
    PAYMENT_METHODS, RETURN_POLICIES, SIZE_GUIDE,
    ORDER_STATUSES, get_status_info
)

# Load environment variables
load_dotenv()

# ===============================================
# CONFIGURATION
# ===============================================

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Parse admin IDs from comma-separated string
ADMIN_USER_IDS = []
admin_ids_str = os.getenv('ADMIN_USER_IDS', '')
if admin_ids_str:
    ADMIN_USER_IDS = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure Gemini AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None
    logger.warning("GEMINI_API_KEY not set - AI features disabled")


# ===============================================
# SESSION MANAGEMENT
# ===============================================

class UserSession:
    """Manage user session data"""
    
    def __init__(self, user_id: int, username: str = None, first_name: str = None):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.role = "admin" if user_id in ADMIN_USER_IDS else "user"
        self.state = "menu"
        self.data = {}
        self.conversation_history = []
        self.last_activity = datetime.now()
        self.message_count = 0


# Global sessions dict
user_sessions: Dict[int, UserSession] = {}


def get_session(user_id: int, username: str = None, first_name: str = None) -> UserSession:
    """Get or create user session"""
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id, username, first_name)
    else:
        user_sessions[user_id].last_activity = datetime.now()
    return user_sessions[user_id]


def get_user_role(user_id: int) -> str:
    """Determine user role"""
    return "admin" if user_id in ADMIN_USER_IDS else "user"


# ===============================================
# CONVERSATION HISTORY
# ===============================================

class ConversationHistory:
    """Manage AI conversation history per user"""
    
    MAX_HISTORY = 10
    
    @staticmethod
    def add_message(session: UserSession, user_msg: str, ai_response: str):
        """Add message pair to history"""
        session.conversation_history.append({
            'user': user_msg,
            'assistant': ai_response,
            'timestamp': datetime.now()
        })
        
        # Limit history size
        if len(session.conversation_history) > ConversationHistory.MAX_HISTORY:
            session.conversation_history = session.conversation_history[-ConversationHistory.MAX_HISTORY:]
    
    @staticmethod
    def get_context(session: UserSession, last_n: int = 4) -> str:
        """Get recent conversation as context"""
        if not session.conversation_history:
            return ""
        
        recent = session.conversation_history[-last_n:]
        context = "\nRECENT CONVERSATION:\n"
        
        for msg in recent:
            context += f"User: {msg['user']}\n"
            context += f"Assistant: {msg['assistant']}\n"
        
        return context
    
    @staticmethod
    def clear(session: UserSession):
        """Clear conversation history"""
        session.conversation_history = []


# ===============================================
# KEYBOARD LAYOUTS
# ===============================================

def get_admin_menu() -> InlineKeyboardMarkup:
    """Get admin menu keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard"),
            InlineKeyboardButton("📦 Orders", callback_data="admin_orders")
        ],
        [
            InlineKeyboardButton("💰 Sales", callback_data="admin_sales"),
            InlineKeyboardButton("📉 Inventory", callback_data="admin_inventory")
        ],
        [
            InlineKeyboardButton("👥 Users", callback_data="admin_users"),
            InlineKeyboardButton("🤖 AI Assistant", callback_data="admin_ai")
        ],
        [
            InlineKeyboardButton("🔄 Refresh Data", callback_data="refresh_data")
        ]
    ])


def get_user_menu() -> InlineKeyboardMarkup:
    """Get user menu keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🤖 Chat with AI", callback_data="user_ai_chat")
        ],
        [
            InlineKeyboardButton("📦 Track Order", callback_data="user_track_order"),
            InlineKeyboardButton("🛍️ Products", callback_data="user_products")
        ],
        [
            InlineKeyboardButton("ℹ️ About Us", callback_data="user_about"),
            InlineKeyboardButton("📱 Contact", callback_data="user_contact")
        ],
        [
            InlineKeyboardButton("💬 Support", callback_data="user_support")
        ]
    ])


def get_back_button(callback_data: str = "back_menu") -> InlineKeyboardMarkup:
    """Get back button keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Menu", callback_data=callback_data)]
    ])


def get_track_method_menu() -> InlineKeyboardMarkup:
    """Get order tracking method menu"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📱 Track by Phone", callback_data="track_by_phone"),
            InlineKeyboardButton("🆔 Track by Order ID", callback_data="track_by_id")
        ],
        [InlineKeyboardButton("◀️ Back", callback_data="back_menu")]
    ])


# ===============================================
# COMMAND HANDLERS
# ===============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - entry point"""
    user = update.effective_user
    session = get_session(user.id, user.username, user.first_name)
    session.state = "menu"
    
    if session.role == "admin":
        await update.message.reply_text(
            f"👋 Welcome back, **{user.first_name}**!\n\n"
            "🔐 **ADMIN MODE**\n"
            "You have full access to business management features.\n\n"
            "Choose an option below:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_admin_menu()
        )
    else:
        await update.message.reply_text(
            f"👋 Welcome to **Nongor Premium**, {user.first_name}!\n\n"
            "🛍️ Your one-stop shop for premium clothing in Bangladesh.\n\n"
            "How can I help you today?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_user_menu()
        )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu command - show menu"""
    await start(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user = update.effective_user
    session = get_session(user.id)
    
    if session.role == "admin":
        text = """
📚 **ADMIN COMMANDS**

/start - Main menu
/menu - Show menu
/dashboard - Business dashboard
/orders - Recent orders
/sales - Sales analytics
/inventory - Stock levels
/ai - AI business assistant
/refresh - Refresh cached data

💡 Use buttons for easy navigation!
"""
    else:
        text = """
📚 **AVAILABLE COMMANDS**

/start - Main menu
/menu - Show menu
/track - Track your order
/products - Browse products
/about - About Nongor
/contact - Contact us
/support - Customer support
/ai - Chat with AI assistant

💡 Use buttons for easy navigation!
"""
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ===============================================
# ADMIN FEATURES
# ===============================================

async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display admin dashboard with business metrics"""
    query = update.callback_query
    if query:
        await query.answer()
    
    db = get_database()
    
    # Fetch stats
    today = db.get_today_stats()
    weekly = db.get_weekly_stats()
    recent_orders = db.get_recent_orders(limit=5)
    low_stock = db.get_low_stock_items(threshold=10)
    status_counts = db.get_order_count_by_status()
    
    # Format dashboard
    text = """
📊 **BUSINESS DASHBOARD**
═══════════════════════════════

**TODAY'S PERFORMANCE:**
📦 Orders: {today_orders}
💰 Revenue: ৳{today_revenue:,.2f}

**THIS WEEK:**
📦 Orders: {week_orders}
💰 Revenue: ৳{week_revenue:,.2f}
💳 Avg Order: ৳{avg_order:,.2f}

**ORDER STATUS:**
⏳ Pending: {pending}
📦 Processing: {processing}
🚚 Shipped: {shipped}
✅ Delivered: {delivered}

**RECENT ORDERS:**
""".format(
        today_orders=today.get('order_count', 0),
        today_revenue=float(today.get('total_revenue', 0) or 0),
        week_orders=weekly.get('order_count', 0),
        week_revenue=float(weekly.get('total_revenue', 0) or 0),
        avg_order=float(weekly.get('avg_order_value', 0) or 0),
        pending=status_counts.get('pending', 0),
        processing=status_counts.get('processing', 0),
        shipped=status_counts.get('shipped', 0),
        delivered=status_counts.get('delivered', 0)
    )
    
    # Add recent orders
    for order in recent_orders[:5]:
        status_info = get_status_info(order.get('status', 'pending'))
        text += f"{status_info['emoji']} #{order.get('order_id', 'N/A')} - {order.get('customer_name', 'N/A')[:15]} - ৳{order.get('total', 0):,.0f}\n"
    
    # Add low stock alerts
    if low_stock:
        text += "\n⚠️ **LOW STOCK ALERTS:**\n"
        for item in low_stock[:3]:
            text += f"• {item['name']}: {item['stock_quantity']} left\n"
    
    text += f"\n🕐 Updated: {datetime.now().strftime('%I:%M %p')}"
    
    # Send or edit message
    if query:
        await query.edit_message_text(
            text, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display recent orders"""
    query = update.callback_query
    if query:
        await query.answer()
    
    db = get_database()
    orders = db.get_recent_orders(limit=10)
    
    text = """
📦 **RECENT ORDERS**
═══════════════════════════════

"""
    
    for order in orders:
        status_info = get_status_info(order.get('status', 'pending'))
        payment = "💳 " + (order.get('payment_status', 'pending')).upper()
        
        text += f"""
{status_info['emoji']} **#{order.get('order_id', 'N/A')}** - {status_info['label']}
👤 {order.get('customer_name', 'N/A')} | 📱 {order.get('customer_phone', 'N/A')}
💰 ৳{order.get('total', 0):,.0f} | {payment}
───────────────────────────────
"""
    
    text += f"\n📊 Total Active Orders: {len(orders)}"
    text += f"\n🕐 {datetime.now().strftime('%I:%M %p')}"
    
    if query:
        await query.edit_message_text(
            text[:4096],  # Telegram message limit
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
    else:
        await update.message.reply_text(
            text[:4096],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )


async def admin_sales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display sales analytics"""
    query = update.callback_query
    if query:
        await query.answer()
    
    db = get_database()
    
    today = db.get_today_stats()
    weekly = db.get_weekly_stats()
    monthly = db.get_monthly_stats()
    top_products = db.get_top_products(days=30, limit=5)
    
    text = """
💰 **SALES ANALYTICS**
═══════════════════════════════

**REVENUE OVERVIEW:**
📅 Today: ৳{today_rev:,.2f}
📆 This Week: ৳{week_rev:,.2f}
📈 This Month: ৳{month_rev:,.2f}

**🏆 TOP PRODUCTS (30 days):**
""".format(
        today_rev=float(today.get('total_revenue', 0) or 0),
        week_rev=float(weekly.get('total_revenue', 0) or 0),
        month_rev=float(monthly.get('total_revenue', 0) or 0)
    )
    
    for i, p in enumerate(top_products, 1):
        text += f"""{i}. **{p['product_name'][:25]}**
   💰 ৳{float(p.get('revenue', 0)):,.0f} | 📦 {p.get('order_count', 0)} orders
"""
    
    # Insights
    avg_order = float(weekly.get('avg_order_value', 0) or 0)
    text += f"""
**📊 INSIGHTS:**
• Avg order value: ৳{avg_order:,.0f}
• Weekly orders: {weekly.get('order_count', 0)}
• Monthly orders: {monthly.get('order_count', 0)}

🕐 Updated: {datetime.now().strftime('%I:%M %p')}
"""
    
    if query:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )


async def admin_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display inventory status"""
    query = update.callback_query
    if query:
        await query.answer()
    
    db = get_database()
    
    inventory = db.get_total_inventory()
    low_stock = db.get_low_stock_items(threshold=10)
    out_of_stock = db.get_out_of_stock_items()
    products = db.get_available_products()
    
    text = """
📉 **INVENTORY STATUS**
═══════════════════════════════

**OVERVIEW:**
🏷️ Total Products: {total_products}
📦 Total Stock: {total_units} units
✅ Well Stocked: {well_stocked}
⚠️ Low Stock: {low_stock_count}
❌ Out of Stock: {out_of_stock_count}

""".format(
        total_products=inventory.get('total_products', 0),
        total_units=inventory.get('total_units', 0),
        well_stocked=inventory.get('well_stocked', 0),
        low_stock_count=inventory.get('low_stock', 0),
        out_of_stock_count=inventory.get('out_of_stock', 0)
    )
    
    if low_stock:
        text += "**⚠️ LOW STOCK ALERTS:**\n"
        for item in low_stock[:5]:
            emoji = "🔴" if item['stock_quantity'] < 5 else "🟡"
            text += f"{emoji} {item['name']}: {item['stock_quantity']} left\n"
        text += "\n"
    
    if out_of_stock:
        text += "**❌ OUT OF STOCK:**\n"
        for item in out_of_stock[:5]:
            text += f"• {item['name']}\n"
        text += "\n"
    
    # Well stocked items
    well_stocked = [p for p in products if p.get('stock_quantity', 0) > 20][:5]
    if well_stocked:
        text += "**✅ WELL STOCKED:**\n"
        for item in well_stocked:
            text += f"• {item['name']}: {item['stock_quantity']}\n"
    
    text += f"\n🕐 {datetime.now().strftime('%I:%M %p')}"
    
    if query:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )


async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display user statistics"""
    query = update.callback_query
    if query:
        await query.answer()
    
    db = get_database()
    
    # Count sessions
    total_sessions = len(user_sessions)
    admin_count = len(ADMIN_USER_IDS)
    user_count = total_sessions - sum(1 for s in user_sessions.values() if s.role == 'admin')
    
    # Active in last 24 hours
    now = datetime.now()
    active_24h = sum(1 for s in user_sessions.values() 
                     if (now - s.last_activity).total_seconds() < 86400)
    
    # Message counts
    total_messages = sum(s.message_count for s in user_sessions.values())
    
    text = f"""
👥 **USER STATISTICS**
═══════════════════════════════

**OVERVIEW:**
👨‍💼 Total Admins: {admin_count}
👤 Regular Users: {user_count}
✅ Active (24h): {active_24h}
📱 Total Sessions: {total_sessions}

**🔐 ADMIN LIST:**
"""
    
    for admin_id in ADMIN_USER_IDS:
        session = user_sessions.get(admin_id)
        name = session.first_name if session else "Unknown"
        text += f"• {name} (ID: {admin_id})\n"
    
    text += f"""
**📊 ACTIVITY:**
• Total messages: {total_messages}
• AI conversations: {sum(len(s.conversation_history) for s in user_sessions.values())}

🕐 {datetime.now().strftime('%I:%M %p')}
"""
    
    if query:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )


# ===============================================
# USER FEATURES
# ===============================================

async def user_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display available products"""
    query = update.callback_query
    if query:
        await query.answer()
    
    db = get_database()
    products = db.get_available_products()
    
    text = """
🛍️ **AVAILABLE PRODUCTS**
═══════════════════════════════

"""
    
    for p in products[:15]:
        availability = p.get('availability', 'in_stock')
        if availability == 'in_stock':
            emoji = "✅"
            status = f"In Stock ({p.get('stock_quantity', 0)} units)"
        elif availability == 'low_stock':
            emoji = "⚠️"
            status = f"Limited ({p.get('stock_quantity', 0)} left)"
        else:
            emoji = "❌"
            status = "Out of Stock"
        
        text += f"{emoji} **{p['name']}**\n   {status}\n\n"
    
    text += f"""
📱 Need help choosing?
Chat with our AI assistant or contact:
• WhatsApp: {CONTACT_INFO['whatsapp']}
• Website: {CONTACT_INFO['website']}
"""
    
    if query:
        await query.edit_message_text(
            text[:4096],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
    else:
        await update.message.reply_text(
            text[:4096],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )


async def user_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display about us information"""
    query = update.callback_query
    if query:
        await query.answer()
    
    text = f"""
ℹ️ **ABOUT NONGOR PREMIUM**
═══════════════════════════════

🎨 **Who We Are**
Premium clothing brand delivering style, quality, 
and comfort to fashion-conscious individuals 
across Bangladesh.

✨ **Our Promise**
✅ Premium quality materials
✅ Trendy, modern designs
✅ Fast & reliable delivery
✅ Excellent customer service
✅ Competitive prices

🌐 **Connect With Us**
• Website: {CONTACT_INFO['website']}
• Facebook: {CONTACT_INFO['facebook']}
• WhatsApp: {CONTACT_INFO['whatsapp']}
• Email: {CONTACT_INFO['email']}

🕐 **Business Hours**
{BUSINESS_HOURS['weekdays']['days']}: {BUSINESS_HOURS['weekdays']['hours']}
{BUSINESS_HOURS['friday']['days']}: {BUSINESS_HOURS['friday']['hours']}

🚚 **Delivery**
• Dhaka: {DELIVERY_POLICIES['dhaka']['time']}
• Outside Dhaka: {DELIVERY_POLICIES['outside_dhaka']['time']}
• Free shipping on orders ৳{DELIVERY_POLICIES['dhaka']['free_above']}+

Thank you for choosing Nongor! 💚
"""
    
    if query:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )


async def user_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display contact information"""
    query = update.callback_query
    if query:
        await query.answer()
    
    text = f"""
📱 **CONTACT US**
═══════════════════════════════

**Get in Touch:**

📞 **Phone/WhatsApp**
{CONTACT_INFO['phone']}

📧 **Email**
{CONTACT_INFO['email']}

💬 **Facebook**
{CONTACT_INFO['facebook']}

🌐 **Website**
{CONTACT_INFO['website']}

🕐 **Business Hours**
{BUSINESS_HOURS['weekdays']['days']}: {BUSINESS_HOURS['weekdays']['hours']}
{BUSINESS_HOURS['friday']['days']}: {BUSINESS_HOURS['friday']['hours']}

**Response Times:**
• WhatsApp: {BUSINESS_HOURS['response_times']['whatsapp']} ⚡
• Email: {BUSINESS_HOURS['response_times']['email']}
• Facebook: {BUSINESS_HOURS['response_times']['facebook']}

Looking forward to hearing from you! 💚
"""
    
    if query:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )


async def user_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display customer support options"""
    query = update.callback_query
    if query:
        await query.answer()
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Chat with AI", callback_data="user_ai_chat")],
        [InlineKeyboardButton("📦 Track My Order", callback_data="user_track_order")],
        [InlineKeyboardButton("📱 WhatsApp Support", url=f"https://wa.me/{CONTACT_INFO['whatsapp'].replace('+', '').replace(' ', '')}")],
        [InlineKeyboardButton("◀️ Back", callback_data="back_menu")]
    ])
    
    text = f"""
💬 **CUSTOMER SUPPORT**
═══════════════════════════════

**Need Help?**

🤖 **Chat with AI**
Get instant answers to common questions

📦 **Track Your Order**
Check order status and delivery updates

📱 **Direct Contact**
WhatsApp: {CONTACT_INFO['whatsapp']}
Email: {CONTACT_INFO['email']}

**Common Topics:**
• Order tracking
• Payment issues
• Product questions
• Sizing help
• Returns & exchanges
• Delivery inquiries

**Response Time:**
• AI Chat: Instant ⚡
• WhatsApp: {BUSINESS_HOURS['response_times']['whatsapp']}
• Email: {BUSINESS_HOURS['response_times']['email']}

We're here to help! 💚
"""
    
    if query:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )


# ===============================================
# ORDER TRACKING
# ===============================================

async def user_track_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show order tracking method options"""
    query = update.callback_query
    if query:
        await query.answer()
    
    text = """
📦 **TRACK YOUR ORDER**
═══════════════════════════════

Choose how you want to track:

📱 **By Phone Number**
Enter the phone number you used when ordering

🆔 **By Order ID**
Enter your order ID (e.g., 12345 or #NG-1234)
"""
    
    if query:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_track_method_menu()
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_track_method_menu()
        )


async def track_by_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for phone number"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    session = get_session(user.id)
    session.state = "waiting_phone"
    
    await query.edit_message_text(
        "📱 **Track by Phone Number**\n\n"
        "Please enter your phone number (11 digits):\n"
        "_Example: 01711222333_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_button()
    )


async def track_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for order ID"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    session = get_session(user.id)
    session.state = "waiting_order_id"
    
    await query.edit_message_text(
        "🆔 **Track by Order ID**\n\n"
        "Please enter your order ID:\n"
        "_Example: 12345 or #NG-1234_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_button()
    )


async def process_phone_tracking(update: Update, message: str):
    """Process phone number for tracking"""
    # Extract phone number
    phone_pattern = r'01[3-9]\d{8}'
    match = re.search(phone_pattern, message.replace(' ', '').replace('-', ''))
    
    if not match:
        await update.message.reply_text(
            "❌ Invalid phone number format.\n\n"
            "Please enter a valid 11-digit Bangladesh phone number.\n"
            "_Example: 01711222333_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
        return
    
    phone = match.group(0)
    
    await update.message.reply_text("🔍 Searching for your order...")
    
    order = await get_order_details(phone=phone)
    order_text = await format_order_details(order)
    
    await update.message.reply_text(
        order_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_button()
    )


async def process_id_tracking(update: Update, message: str):
    """Process order ID for tracking"""
    # Extract order ID
    order_pattern = r'#?(?:NG-)?(\d{1,6})'
    match = re.search(order_pattern, message, re.IGNORECASE)
    
    if not match:
        await update.message.reply_text(
            "❌ Invalid order ID format.\n\n"
            "Please enter a valid order ID.\n"
            "_Example: 12345 or #NG-1234_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
        return
    
    order_id = int(match.group(1))
    
    await update.message.reply_text("🔍 Looking up your order...")
    
    order = await get_order_details(order_id=order_id)
    order_text = await format_order_details(order)
    
    await update.message.reply_text(
        order_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_button()
    )


# ===============================================
# AI CHAT
# ===============================================

async def start_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str = "user"):
    """Start AI chat session"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user = update.effective_user
    session = get_session(user.id)
    session.state = f"{mode}_ai_chat"
    
    if mode == "admin":
        text = """
🤖 **AI BUSINESS ASSISTANT**
═══════════════════════════════

I'm your AI-powered business assistant. I can help with:

📊 Sales analysis and insights
📦 Inventory recommendations
📈 Trend analysis
💡 Marketing suggestions
📝 Report generation

**Ask me anything about your business!**

_Type your question or use /menu to exit._
"""
    else:
        text = """
🤖 **AI SHOPPING ASSISTANT**
═══════════════════════════════

Hi! I'm your AI shopping assistant. I can help with:

🛍️ Product recommendations
📏 Size guidance
📦 Order tracking
❓ Answer questions
💡 Shopping tips

**Ask me anything!**

_Type your question or use /menu to exit._
"""
    
    if query:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )


async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
    """Handle AI chat messages"""
    user = update.effective_user
    session = get_session(user.id)
    session.message_count += 1
    
    if not ai_model:
        await update.message.reply_text(
            "⚠️ AI is currently unavailable. Please contact support.",
            reply_markup=get_back_button()
        )
        return
    
    # Check for order tracking in message
    order_response = await detect_order_inquiry(message)
    if order_response:
        await update.message.reply_text(
            order_response,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
        return
    
    # Get context based on role
    role = "admin" if "admin" in session.state else "user"
    ai_context = await get_full_ai_context(role)
    
    # Add conversation history
    history_context = ConversationHistory.get_context(session)
    
    # Build prompt
    full_prompt = f"{ai_context}\n{history_context}\n\nUser message: {message}"
    
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Generate response
        response = ai_model.generate_content(full_prompt)
        ai_response = response.text
        
        # Store in history
        ConversationHistory.add_message(session, message, ai_response)
        
        # Send response
        await update.message.reply_text(
            ai_response[:4096],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
        
    except Exception as e:
        logger.error(f"AI error: {e}")
        await update.message.reply_text(
            "⚠️ I encountered an issue. Please try again or contact support.",
            reply_markup=get_back_button()
        )


async def detect_order_inquiry(message: str) -> Optional[str]:
    """Detect and handle order tracking in messages"""
    # Keywords indicating order inquiry
    order_keywords = [
        'order', 'track', 'delivery', 'shipped', 'status', 'where is',
        'আমার অর্ডার', 'ডেলিভারি', 'কোথায়'
    ]
    
    message_lower = message.lower()
    
    # Check for keywords
    has_keyword = any(kw in message_lower for kw in order_keywords)
    
    if not has_keyword:
        return None
    
    # Try to extract phone number
    phone_pattern = r'01[3-9]\d{8}'
    phone_match = re.search(phone_pattern, message.replace(' ', '').replace('-', ''))
    
    if phone_match:
        phone = phone_match.group(0)
        order = await get_order_details(phone=phone)
        return await format_order_details(order)
    
    # Try to extract order ID
    order_pattern = r'#?(?:NG-)?(\d{1,6})'
    order_match = re.search(order_pattern, message, re.IGNORECASE)
    
    if order_match:
        order_id = int(order_match.group(1))
        order = await get_order_details(order_id=order_id)
        return await format_order_details(order)
    
    # Keyword found but no ID/phone - ask for info
    return """📦 I can help you track your order!

Please provide:
• Your phone number (e.g., 01711222333), OR
• Your order ID (e.g., #12345)"""


# ===============================================
# CALLBACK HANDLER
# ===============================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    data = query.data
    user = update.effective_user
    session = get_session(user.id)
    
    # Route to appropriate handler
    handlers = {
        # Admin handlers
        'admin_dashboard': admin_dashboard,
        'admin_orders': admin_orders,
        'admin_sales': admin_sales,
        'admin_inventory': admin_inventory,
        'admin_users': admin_users,
        'admin_ai': lambda u, c: start_ai_chat(u, c, "admin"),
        
        # User handlers
        'user_ai_chat': lambda u, c: start_ai_chat(u, c, "user"),
        'user_track_order': user_track_order,
        'user_products': user_products,
        'user_about': user_about,
        'user_contact': user_contact,
        'user_support': user_support,
        
        # Tracking handlers
        'track_by_phone': track_by_phone,
        'track_by_id': track_by_id,
        
        # Utility handlers
        'back_menu': back_to_menu,
        'refresh_data': refresh_data,
    }
    
    handler = handlers.get(data)
    if handler:
        await handler(update, context)
    else:
        await query.answer("Feature coming soon!", show_alert=True)


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to main menu"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    session = get_session(user.id)
    session.state = "menu"
    
    if session.role == "admin":
        await query.edit_message_text(
            f"👋 **Admin Menu**\n\n"
            "Choose an option:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_admin_menu()
        )
    else:
        await query.edit_message_text(
            f"👋 **Main Menu**\n\n"
            "How can I help you?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_user_menu()
        )


async def refresh_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh cached data"""
    query = update.callback_query
    await query.answer("Refreshing data...")
    
    clear_context_cache()
    
    await admin_dashboard(update, context)


# ===============================================
# MESSAGE HANDLER
# ===============================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages"""
    user = update.effective_user
    message = update.message.text
    session = get_session(user.id)
    state = session.state
    
    # Route based on state
    if state == 'admin_ai_chat' or state == 'user_ai_chat':
        await handle_ai_chat(update, context, message)
    
    elif state == 'waiting_phone':
        session.state = 'menu'
        await process_phone_tracking(update, message)
    
    elif state == 'waiting_order_id':
        session.state = 'menu'
        await process_id_tracking(update, message)
    
    else:
        # Check if it's an order inquiry
        order_response = await detect_order_inquiry(message)
        if order_response:
            await update.message.reply_text(
                order_response,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_back_button()
            )
        else:
            # Suggest using menu
            keyboard = get_admin_menu() if session.role == "admin" else get_user_menu()
            await update.message.reply_text(
                "💡 Use the menu buttons below to navigate!\n\n"
                "Or type /help to see available commands.",
                reply_markup=keyboard
            )


# ===============================================
# ERROR HANDLER
# ===============================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors gracefully"""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again or contact support.\n\n"
                f"📱 WhatsApp: {CONTACT_INFO['whatsapp']}"
            )
    except:
        pass


# ===============================================
# MAIN
# ===============================================

async def run_bot():
    """Start the bot asynchronously"""
    if not TELEGRAM_BOT_TOKEN:
        print("[ERROR] TELEGRAM_BOT_TOKEN not set!")
        return
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("help", help_command))
    
    # Admin command shortcuts
    application.add_handler(CommandHandler("dashboard", admin_dashboard))
    application.add_handler(CommandHandler("orders", admin_orders))
    application.add_handler(CommandHandler("sales", admin_sales))
    application.add_handler(CommandHandler("inventory", admin_inventory))
    
    # User command shortcuts
    application.add_handler(CommandHandler("track", user_track_order))
    application.add_handler(CommandHandler("products", user_products))
    application.add_handler(CommandHandler("about", user_about))
    application.add_handler(CommandHandler("contact", user_contact))
    application.add_handler(CommandHandler("support", user_support))
    
    # AI command
    application.add_handler(CommandHandler("ai", lambda u, c: start_ai_chat(u, c, get_user_role(u.effective_user.id))))
    
    # Refresh command
    application.add_handler(CommandHandler("refresh", refresh_data))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handler (must be last)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start polling
    print("[INFO] Nongor Bot V3 starting...")
    print(f"[INFO] Admin IDs: {ADMIN_USER_IDS}")
    
    # Initialize and start
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    print("[INFO] Bot is running! Press Ctrl+C to stop.")
    
    # Run until stopped
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        # Cleanup
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def main():
    """Entry point"""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n[INFO] Bot stopped by user.")


if __name__ == "__main__":
    main()
