# Nongor Bot V3 - Documentation

<div align="center">

# 🤖 Nongor Telegram Bot V3

### Dual-Mode Business Management & Customer Service Bot

**Admin Management + AI Shopping Assistant**

[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI-8E75B2?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)

</div>

---

## 📑 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Commands](#-commands)
- [API Reference](#-api-reference)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

### 🔐 Admin Mode
| Feature | Description |
|---------|-------------|
| 📊 Dashboard | Real-time business metrics, today/weekly stats |
| 📦 Orders | View recent orders with status and details |
| 💰 Sales | Revenue analytics, top products, trends |
| 📉 Inventory | Stock levels, low stock alerts, out of stock |
| 👥 Users | Session statistics, admin list |
| 🤖 AI Assistant | Business insights, analytics interpretation |

### 👤 User Mode
| Feature | Description |
|---------|-------------|
| 🤖 AI Chat | Product recommendations, sizing help, Q&A |
| 📦 Order Tracking | Track by phone or order ID |
| 🛍️ Products | Browse available products with stock status |
| ℹ️ About | Brand information |
| 📱 Contact | Contact details and business hours |
| 💬 Support | Customer support options |

### 🧠 Smart Features
- **Auto-detect order inquiries** - Recognizes phone numbers and order IDs in messages
- **AI context building** - Real-time database + website + policies context
- **Session management** - Per-user state and conversation history
- **Rate limiting** - Protects against spam
- **Caching** - 5-minute context cache for performance

---

## 🏗️ Architecture

```
nongor_bot_v3/
├── bot_v3_enhanced.py      # Main bot (900+ lines)
│   ├── Session Management
│   ├── Admin Handlers
│   ├── User Handlers
│   ├── AI Chat
│   └── Order Tracking
│
├── database_enhanced.py    # Database layer (400+ lines)
│   ├── Connection pooling
│   ├── Order queries
│   ├── Product queries
│   └── Analytics queries
│
├── ai_context_builder.py   # AI context (350+ lines)
│   ├── Database context
│   ├── Website scraping
│   ├── Business policies
│   └── Caching system
│
├── config/
│   └── business_config.py  # Static configuration
│
├── requirements.txt        # Dependencies
├── .env.example           # Config template
└── README_V3.md           # This file
```

---

## 🚀 Installation

### Prerequisites
- Python 3.8+
- PostgreSQL database (Neon recommended)
- Telegram Bot Token
- Google Gemini API Key

### Steps

```bash
# 1. Navigate to bot directory
cd Bot/nongor_bot_v3

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Edit .env with your credentials

# 5. Run the bot
python bot_v3_enhanced.py
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `ADMIN_USER_IDS` | ✅ | Comma-separated admin Telegram IDs |
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `NETLIFY_DATABASE_URL` | ✅ | PostgreSQL connection string |
| `WEBSITE_URL` | ❌ | Website URL for scraping |
| `ENABLE_WEB_SCRAPING` | ❌ | Enable/disable scraping (default: true) |

### Getting Your Telegram ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will reply with your user ID
3. Add this ID to `ADMIN_USER_IDS` in `.env`

---

## 📖 Usage

### Admin Guide

1. Start the bot with `/start`
2. You'll see the Admin Menu with:
   - 📊 Dashboard - Business overview
   - 📦 Orders - Recent orders list
   - 💰 Sales - Revenue analytics
   - 📉 Inventory - Stock levels
   - 👥 Users - User statistics
   - 🤖 AI - Business insights

### User Guide

1. Start the bot with `/start`
2. You'll see the User Menu with:
   - 🤖 Chat with AI - Ask questions
   - 📦 Track Order - Find your order
   - 🛍️ Products - Browse catalog
   - ℹ️ About - Brand info
   - 📱 Contact - Get in touch

### Order Tracking

Users can track orders by:
1. **Phone number**: Just mention your phone (01711222333)
2. **Order ID**: Say "order #12345" or "track 12345"

The bot auto-detects these in messages!

---

## 🔧 Commands

### Universal Commands
| Command | Description |
|---------|-------------|
| `/start` | Main menu |
| `/menu` | Show menu |
| `/help` | List commands |
| `/ai` | Start AI chat |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/dashboard` | Business dashboard |
| `/orders` | Recent orders |
| `/sales` | Sales analytics |
| `/inventory` | Stock levels |
| `/refresh` | Refresh cached data |

### User Commands
| Command | Description |
|---------|-------------|
| `/track` | Track order |
| `/products` | Product catalog |
| `/about` | About Nongor |
| `/contact` | Contact info |
| `/support` | Support options |

---

## 📚 API Reference

### Database Methods

```python
from database_enhanced import get_database

db = get_database()

# Orders
order = db.get_order_by_id(12345)
order = db.get_order_by_phone("01711222333")
orders = db.get_recent_orders(limit=10)

# Products
products = db.get_available_products()
results = db.search_products("hoodie")
low_stock = db.get_low_stock_items(threshold=10)

# Analytics
today = db.get_today_stats()
weekly = db.get_weekly_stats()
top = db.get_top_products(days=30, limit=5)
```

### AI Context Builder

```python
from ai_context_builder import (
    get_full_ai_context,
    get_order_details,
    format_order_details
)

# Get AI context
context = await get_full_ai_context(user_role="user")

# Order tracking
order = await get_order_details(phone="01711222333")
formatted = await format_order_details(order)
```

---

## 🔍 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Bot not responding | Check `TELEGRAM_BOT_TOKEN` |
| "AI unavailable" | Check `GEMINI_API_KEY` |
| No database data | Check `NETLIFY_DATABASE_URL` |
| Admin features not showing | Check `ADMIN_USER_IDS` |

### Logs

Logs are saved to `bot.log` in the bot directory.

```bash
# View logs
type bot.log  # Windows
cat bot.log   # Linux/Mac
```

### Testing Connection

```python
from database_enhanced import get_database

db = get_database()
if db.test_connection():
    print("✅ Database connected!")
else:
    print("❌ Database connection failed")
```

---

## 📝 License

© 2026 Nongor Premium. All Rights Reserved.

---

<div align="center">

**Built with ❤️ for Nongor Premium**

[Website](https://nongor-brand.vercel.app) • [Facebook](https://facebook.com/nongor) • [Support](mailto:support@nongor.com)

</div>
