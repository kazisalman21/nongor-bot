from js import Response, fetch
import json
import logging
import re
from datetime import datetime
from typing import Optional, Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode
from telegram.error import BadRequest

import google.generativeai as genai

# ⚠️ CRITICAL: database.py must be in the same src/ folder as this file
from database import Database

# ===============================================
# GLOBAL STATE & CONFIG
# ===============================================
application = None
db = None
ai_initialized = False

logger = logging.getLogger(__name__)

# Constants
ADMIN_USER_IDS = []
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
        self.conversation_history = []
        self.last_activity = datetime.now()

user_sessions = {}

def get_session(user_id, username=None, first_name=None):
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id, username, first_name)
    return user_sessions[user_id]

# ===============================================
# INITIALIZATION
# ===============================================

async def initialize_app(env):
    global application, db, ai_initialized, ADMIN_USER_IDS
    
    if application is not None:
        return application
    
    # Load Admin IDs from env
    admin_str = getattr(env, "ADMIN_USER_IDS", "")
    ADMIN_USER_IDS = [int(i.strip()) for i in admin_str.split(",") if i.strip().isdigit()]

    # Initialize Database
    db = Database(env.DATABASE_URL)
    
    # Configure Gemini AI
    if getattr(env, "GEMINI_API_KEY", None):
        try:
            genai.configure(api_key=env.GEMINI_API_KEY)
            ai_initialized = True
        except Exception as e:
            logger.error(f"AI initialization failed: {e}")

    # Build Application
    application = Application.builder().token(env.TELEGRAM_BOT_TOKEN).build()
    
    # Register Handlers
    register_handlers(application)
    
    await application.initialize()
    return application

def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("help", help_command))
    
    # Ported Admin Commands
    app.add_handler(CommandHandler("dashboard", admin_dashboard))
    app.add_handler(CommandHandler("orders", admin_orders))
    app.add_handler(CommandHandler("sales", admin_sales))
    app.add_handler(CommandHandler("inventory", admin_inventory))
    
    # User Command Shortcuts
    app.add_handler(CommandHandler("track", user_track_order))
    app.add_handler(CommandHandler("products", user_products))
    app.add_handler(CommandHandler("about", user_about))
    app.add_handler(CommandHandler("contact", user_contact))
    app.add_handler(CommandHandler("support", user_support))
    
    # Callback Query
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Message Handler (Handles States & AI)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ===============================================
# KEYBOARDS
# ===============================================

def get_admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard"),
         InlineKeyboardButton("📦 Orders", callback_data="admin_orders")],
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
# HANDLERS implementation
# ===============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    # Handle both message and callback query
    if update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_USER_IDS
    text = "📚 **ADMIN COMMANDS**\n/start, /menu, /dashboard, /orders, /sales, /inventory" if is_admin else \
           "📚 **USER COMMANDS**\n/start, /menu, /track, /products, /about, /contact, /support"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# Admin Handlers
async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS: return
    
    today = await db.get_today_stats()
    weekly = await db.get_weekly_stats()
    users = await db.get_user_stats()
    
    text = f"""📊 **BUSINESS DASHBOARD**

**TODAY:**
📦 Orders: {today.get('order_count', 0)}
💰 Revenue: ৳{today.get('total_revenue', 0):,.2f}

**WEEKLY:**
📦 Orders: {weekly.get('order_count', 0)}
💰 Revenue: ৳{weekly.get('total_revenue', 0):,.2f}

**USERS:**
👥 Total: {users.get('total_users', 0)}
🔥 Active (7d): {users.get('active_users', 0)}"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS: return
    orders = await db.get_recent_orders(limit=10)
    
    if orders:
        text = "📦 **RECENT ORDERS**\n\n" + "\n".join([
            f"• #{o.get('order_id', 'N/A')} - {o.get('customer_name', 'Unknown')} - ৳{o.get('total', 0):,.0f}" 
            for o in orders
        ])
    else:
        text = "📦 **RECENT ORDERS**\n\nNo orders found."
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())

async def admin_sales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS: return
    top = await db.get_top_products(limit=5)
    
    if top:
        text = "💰 **TOP PRODUCTS**\n\n" + "\n".join([
            f"{i+1}. {p.get('product_name', 'Unknown')}: ৳{p.get('revenue', 0):,.0f}" 
            for i, p in enumerate(top)
        ])
    else:
        text = "💰 **TOP PRODUCTS**\n\nNo sales data available."
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())

async def admin_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USER_IDS: return
    products = await db.get_available_products()
    
    if products:
        text = "📉 **INVENTORY**\n\n" + "\n".join([
            f"• {p.get('name', 'Unknown')}: {p.get('order_count', 0)} orders" 
            for p in products[:15]
        ])
    else:
        text = "📉 **INVENTORY**\n\nNo products found."
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())

# User Handlers
async def user_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = await db.get_available_products()
    
    if products:
        text = "🛍️ **PRODUCTS**\n\n" + "\n".join([
            f"• {p.get('name', 'Unknown')}: ৳{p.get('price', 0):,.0f}" 
            for p in products[:15]
        ])
    else:
        text = "🛍️ **PRODUCTS**\n\nNo products available at the moment."
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())

async def user_track_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📦 **TRACK ORDER**\nPlease enter your phone number or Order ID (e.g., 01711222333 or #12345):"
    session = get_session(update.effective_user.id)
    session.state = "waiting_tracking"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())

async def user_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"""ℹ️ **ABOUT NONGOR PREMIUM**
═══════════════════════════════

🎨 **Who We Are**
Premium clothing brand delivering style, quality, 
and comfort to fashion-conscious individuals in BD.

✨ **Our Promise**
✅ Premium quality materials
✅ Trendy, modern designs
✅ Fast & reliable delivery

🕐 **Business Hours**
{BUSINESS_HOURS['weekdays']['days']}: {BUSINESS_HOURS['weekdays']['hours']}
{BUSINESS_HOURS['friday']['days']}: {BUSINESS_HOURS['friday']['hours']}

🚚 **Delivery**
• Dhaka: {DELIVERY_POLICIES['dhaka']['time']} (৳{DELIVERY_POLICIES['dhaka']['charge']})
• Outside: {DELIVERY_POLICIES['outside']['time']} (৳{DELIVERY_POLICIES['outside']['charge']})
• Free shipping on orders above ৳{DELIVERY_POLICIES['dhaka']['free_above']}

Thank you for choosing Nongor! 💚"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())

async def user_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"""📱 **CONTACT US**
═══════════════════════════════

📞 **Phone/WhatsApp**
{CONTACT_INFO['whatsapp']}

📧 **Email**
{CONTACT_INFO['email']}

🌐 **Website**
{CONTACT_INFO['website']}

🕐 **Business Hours**
{BUSINESS_HOURS['weekdays']['days']}: {BUSINESS_HOURS['weekdays']['hours']}

**Response Times:**
• WhatsApp: {BUSINESS_HOURS['response_times']['whatsapp']} ⚡
• Email: {BUSINESS_HOURS['response_times']['email']}"""

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_button())

async def user_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await user_contact(update, context)

# Message Hub
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
    if not ai_initialized:
        await update.message.reply_text("⚠️ AI features are currently disabled.")
        return
    
    try:
        # Build context
        ctx = await db.get_products_for_context()
        policies = f"Delivery: Dhaka {DELIVERY_POLICIES['dhaka']['time']}, Outside {DELIVERY_POLICIES['outside']['time']}. Free ship > {DELIVERY_POLICIES['dhaka']['free_above']}."
        full_prompt = f"Role: Nongor clothing brand assistant. Be helpful and concise.\n\nPolicies: {policies}\n\nProducts:\n{ctx}\n\nCustomer: {message}"
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(full_prompt)
        reply = response.text
        
        try:
            await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        except BadRequest:
            await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"AI Error: {e}")
        await update.message.reply_text("⚠️ Error generating response. Please try again.")

# Callback Hub - FIXED VERSION
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    session = get_session(user.id, user.username, user.first_name)
    
    data = query.data
    
    if data == "admin_dashboard": 
        await admin_dashboard(update, context)
    elif data == "admin_orders": 
        await admin_orders(update, context)
    elif data == "admin_sales": 
        await admin_sales(update, context)
    elif data == "admin_inventory": 
        await admin_inventory(update, context)
    elif data == "user_products": 
        await user_products(update, context)
    elif data == "user_track_order": 
        await user_track_order(update, context)
    elif data == "user_about": 
        await user_about(update, context)
    elif data == "user_contact": 
        await user_contact(update, context)
    elif data == "user_ai_chat":
        session.state = "ai_chat"
        await query.edit_message_text(
            "💬 **AI Assistant Active**\n\nAsk me anything about our products!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_button()
        )
    elif data == "back_menu":
        # Show menu based on user role
        if session.role == "admin":
            text = f"👋 Welcome back, Admin **{user.first_name}**!\nChoose an option:"
            reply_markup = get_admin_menu()
        else:
            text = f"👋 Salam, **{user.first_name}**! Welcome to Nongor Premium.\nHow can I help you today?"
            reply_markup = get_user_menu()
        
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        except BadRequest:
            # If edit fails (message too old), send new message
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# ===============================================
# ENTRY POINT
# ===============================================

async def on_fetch(request, env):
    try:
        app = await initialize_app(env)
        
        if request.method == "POST":
            body = await request.text()
            data = json.loads(body)
            update = Update.de_json(data, app.bot)
            await app.process_update(update)
            return Response.new("OK", status=200)
        
        return Response.new("Nongor Bot Worker Active", status=200)
        
    except Exception as e:
        logger.error(f"Worker error: {e}")
        return Response.new(f"Error: {str(e)}", status=500)
