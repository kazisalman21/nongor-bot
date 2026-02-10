# Nongor Premium Bot v3.0 (2026 Edition)

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Gemini 1.5](https://img.shields.io/badge/Gemini-1.5_Flash-8E75B2?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech)
[![Fly.io](https://img.shields.io/badge/Deployed_on-Fly.io-24185B?style=for-the-badge&logo=flydotio&logoColor=white)](https://fly.io)

**The Ultimate E-commerce Management Bot for Telegram**
*Admin Dashboard • AI Shopping Assistant • Real-Time Analytics*

</div>

---

## 🌟 Premium Features (v3.0)

### 👑 Admin Control Center
- **📊 Live Dashboard**: Real-time sales, order counts, and revenue tracking.
- **📈 Visual Analytics**: Generate weekly sales charts directly in chat.
- **🚨 Instant Alerts**: Get notified within 60 seconds of new orders.
- **📦 Order Management**: View recent orders with customer details and status.
- **📤 Data Export**: Download full order history as CSV for Excel/Sheets.
- **📉 Inventory Tracking**: Monitor stock levels and get low-stock warnings.

### 🤖 AI Powerhouse
- **RAG-Enabled**: The AI knows your *live* inventory and *current* policies.
- **Smart Recommendations**: Suggests products based on user queries.
- **Context Aware**: Remembers conversation history for natural support.
- **Role-Based**: Acts as a helpful assistant to customers, but a business analyst to admins.

### ⚡ Technology Stack
- **Core**: Python 3.11 + `python-telegram-bot` (Async)
- **Database**: PostgreSQL (Neon) via high-performance `asyncpg` driver.
- **AI**: Google Gemini 1.5 Flash (Latest).
- **Visualization**: `matplotlib` for dynamic chart generation.
- **Deployment**: Dockerized on Fly.io (Firecracker MicroVMs).

---

---

## 🏗️ Architecture

nongor_bot_v3/
├── bot_standard/
│   ├── main.py             # Main bot application
│   ├── database.py         # Asyncpg database layer
│   └── system_prompt.py    # AI system prompt
│
├── requirements.txt        # Dependencies
├── Dockerfile              # Docker configuration
├── fly.toml                # Fly.io configuration
├── .env.example            # Config template
└── README_V3.md            # This file

---

## �️ Installation & Setup

### 1️⃣ Prerequisites
- **Python 3.11+** installed.
- **Git** installed.
- **PostgreSQL Database** (e.g., Neon.tech).
- **Telegram Bot Token** (from @BotFather).
- **Gemini API Key** (from Google AI Studio).

### 2️⃣ Clone & Install
```bash
# Clone the repository
git clone https://github.com/kazisalman21/nongor-bot.git
cd nongor-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3️⃣ Configuration (`.env`)
Create a `.env` file in the root directory:
```ini
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_USER_IDS=123456789,987654321
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
WEBSITE_URL=https://nongor-brand.vercel.app
ENABLE_WEB_SCRAPING=true
```

---

## 🚀 Deployment (Fly.io)

We recommend **Fly.io** for hosting (Standard Python + Docker).

1.  **Install Fly CLI** & Login.
2.  **Initialize App**:
    ```bash
    fly launch
    ```
3.  **Set Secrets**:
    ```bash
    fly secrets set TELEGRAM_BOT_TOKEN=... GEMINI_API_KEY=... DATABASE_URL=...
    ```
4.  **Deploy**:
    ```bash
    fly deploy
    ```

---

## 💻 Git Commands for Updates

To push your latest changes to GitHub:

```bash
# 1. Check status of changed files
git status

# 2. Add all changes
git add .

# 3. Commit changes (add a message)
git commit -m "Upgrade to Premium Bot v3.0"

# 4. Push to remote repository
git push origin main
```

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

### Database Methods (AsyncPG)

```python
from database import Database

# Initialize
db = Database(DATABASE_URL)
await db.connect()

# Orders
order = await db.get_order_by_id(12345)
order = await db.get_order_by_phone("01711222333")
orders = await db.get_recent_orders(limit=10)

# Analytics
today = await db.get_today_stats()
weekly = await db.get_weekly_stats()
```

### AI System

The AI uses a **System Prompt** (`system_prompt.py`) to inject context dynamically.
It retrieves:
- Product Inventory
- Delivery Policies
- Business Hours
- User Session Data

---

## ❓ Troubleshooting

### ❌ "ModuleNotFoundError: asyncpg"
The bot is missing the database driver.
- **Fix**: Run `pip install asyncpg` or check `requirements.txt`.

### ❌ "Database connection failed"
- **Fix**: Check `DATABASE_URL` in `.env` or Fly Secrets. ensuring it starts with `postgresql://`.
- **Fix**: Ensure `sslmode=require` is at the end of the URL.

### ❌ "AttributeError: NoneType has no attribute 'reply_text'"
This happens if a button handler tries to reply to a message that doesn't exist.
- **Fix**: The code has been patched to handle `callback_query.message` correctly.

### ❌ Charts not generating
- **Fix**: Ensure `matplotlib` is installed and the host has fonts available (Fly.io Dockerfile handles this).

---

## � License

© 2026 Nongor Premium. All Rights Reserved.
Built with ❤️ by **Kazi Salman**.

---

<div align="center">

**Built with ❤️ for Nongor Premium**

[Website](https://nongor-brand.vercel.app) • [Facebook](https://facebook.com/nongor) • [Support](mailto:support@nongor.com)

</div>
