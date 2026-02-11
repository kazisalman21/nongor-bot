# 🚢 Nongor Premium Bot v4.0 (AI-Powered)

<div align="center">

![Nongor Bot Banner](https://img.shields.io/badge/Nongor-Premium_Bot-2CA5E0?style=for-the-badge&logo=probot&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)
![AI](https://img.shields.io/badge/AI-Multi_Model_Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)
![Database](https://img.shields.io/badge/DB-PostgreSQL_Neon-336791?style=for-the-badge&logo=postgresql&logoColor=white)

**The Ultimate Intelligence System for E-commerce**
*Multi-Model AI • Strategic Business Analyst • Sales Conversion Expert*

[🚀 Deploy to Fly.io](#-deployment-flyio) • [📚 Admin Guide](#-admin-manual) • [🤖 AI Features](#-ai-intelligence-system)

</div>

---

## 🌟 What makes this "Premium"?

This is not just a chatbot; it's a **full-staff replacement** operating 24/7.

### 🧠 Dual-Persona AI Core
The bot runs two distinct AI personalities simultaneously, ensuring the right tone for the right user:

| Feature | 🛍️ **Customer AI (Sales Manager)** | 💼 **Admin AI (Senior Business Manager)** |
| :--- | :--- | :--- |
| **Persona** | Warm, Energetic, Consultative "Fashion Consultant" | Critical, Data-Driven, Strategic "Executive Advisor" |
| **Goal** | **Drive Sales & Conversion** | **Analyze Profit & Optimize Operations** |
| **Knowledge** | Knows strictly `knowledge_base.md` (Shipping/Returns) | Connects **LIVE** to Database (Revenue, Stock, Orders) |
| **Behavior** | Create urgency, suggest matching items, always close deals | Warns about low stock, identifies top sellers, suggests marketing |
| **Safety** | **Zero Hallucination** on policies (Strict Adherence) | **Full Privacy** (Only speaks to Admin IDs) |

### 🤖 Multi-Model AI Strategy
Each task is routed to the best Gemini model for optimal performance:

| Model | Role | Use Case |
| :--- | :--- | :--- |
| `gemini-2.0-flash-exp` | Customer AI | General chat & sales conversations |
| `gemini-2.5-flash-lite` | Search AI | Product discovery & recommendations |
| `gemini-2.0-pro-exp` | Tracking AI | Order analysis & reassurance |
| `gemini-3-flash-preview` | Report AI | Daily business report insights |
| `gemini-flash-latest` | Admin AI | Business strategy & management |
| `gemini-1.5-flash` | Fallback | Most reliable, used when others fail |

### 📊 Real-Time Business Dashboard
Forget spreadsheets. Ask the Admin AI _"How is business today?"_ and get:
- **Revenue Snapshot**: Today vs. Last Week vs. Last Month.
- **Inventory Alerts**: ⚠️ Warnings for low-stock items that are selling fast.
- **Top Performers**: ⭐ Which products are driving your revenue exactly.
- **Category Analysis**: 📈 Which collection (Panjabi, Saree, etc.) is trending.

### 🛡️ Built-in Protections
- **Rate Limiting**: 5-second cooldown per user on AI chat to prevent API abuse.
- **SSL Encryption**: All database connections use `ssl='require'`.
- **Admin-Only Access**: Sensitive commands restricted to `ADMIN_USER_IDS`.
- **Graceful Fallback**: If the primary AI model fails, automatically switches to a reliable fallback.

---

## 🏗️ Technical Architecture

This project is built for **scale** and **reliability**.

```mermaid
graph TD
    User[User/Customer] -->|Telegram| Bot[Nongor Bot v4]
    Admin[Admin Owner] -->|Telegram| Bot
    
    subgraph "Multi-Model AI Core"
        Bot -->|Route: Customer| SalesAI[Sales AI - Flash Exp]
        Bot -->|Route: Search| SearchAI[Search AI - Flash Lite]
        Bot -->|Route: Tracking| TrackAI[Tracking AI - Pro Exp]
        Bot -->|Route: Admin| BizAI[Admin AI - Flash Latest]
        Bot -->|Route: Reports| ReportAI[Report AI - Flash Preview]
    end
    
    subgraph "Data Layer"
        SalesAI -- Read Only --> KB[Knowledge Base.md]
        BizAI -- Read/Write --> DB[(PostgreSQL Neon)]
        Bot -- AsyncPG --> DB
    end

    subgraph "Background Tasks"
        Bot --> Monitor[Website Monitor]
        Bot --> Reports[Daily Report Scheduler]
        Bot --> Polling[New Order Polling]
    end
    
    subgraph "External"
        SalesAI --> Gemini[Google Gemini Multi-Model]
        BizAI --> Gemini
        SearchAI --> Gemini
        TrackAI --> Gemini
        ReportAI --> Gemini
    end
```

### Key Technologies
- **Python 3.12+**: Asynchronous core using `python-telegram-bot`.
- **AsyncPG**: High-performance non-blocking database driver with connection pooling.
- **Google Gemini (Multi-Model)**: 6 specialized models routed by task context.
- **Matplotlib**: Generates sales trend charts on the fly.
- **httpx**: Async HTTP for website health monitoring.
- **Fly.io**: Deployed on Firecracker MicroVMs for zero-downtime.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
- Python 3.11 or higher.
- A PostgreSQL Database (Recommended: [Neon.tech](https://neon.tech)).
- Telegram Bot Token (@BotFather).
- Gemini API Key (Google AI Studio).

### 2. Local Setup
```bash
# Clone the repository
git clone https://github.com/kazisalman21/nongor-bot.git
cd nongor-bot

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

### 3. Database Setup
Run `schema.sql` in your Neon PostgreSQL console to create required tables:
```bash
psql $DATABASE_URL -f schema.sql
```

This creates:
- `users` — Bot user tracking
- `orders` — Full order management (20+ columns)
- `products` — Product catalog with stock tracking
- `coupons` — Discount code system

### 4. Configuration (.env)
Fill in your credentials in `.env`:
```ini
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
ADMIN_USER_IDS=987654321,123456789
GEMINI_API_KEY=AIzaSy...
DATABASE_URL=postgresql://user:pass@ep-xyz.region.neon.tech/neondb?sslmode=require
WEBSITE_URL=https://your-website.com
```

> **Note**: The legacy env var `NETLIFY_DATABASE_URL` is still supported for backward compatibility.

### 5. Run the Bot
```bash
python bot_standard/main.py
```

### 6. Verify Database Connection
```bash
python test.py
```

---

## 📚 Admin Manual

### 🤖 Commanding the Business AI
As an admin, you have a **Senior Manager** at your disposal. Try these prompts:
- *"Give me a summary of today's sales."* → Returns revenue, order count, and comparison to last week.
- *"What should I restock?"* → Checks inventory < 10 units and cross-references with high sales velocity.
- *"Which category is making the most money?"* → Returns category-wise revenue breakdown.
- *"Find order #1234"* → Fetches customer details, payment status, and courier info.

### ⌨️ Command Reference

**Admin Commands:**

| Command | Action |
| :--- | :--- |
| `/start` | Open the Main Menu |
| `/menu` | Return to Main Menu |
| `/dashboard` | View today's stats with AI-generated tips |
| `/orders` | See last 10 orders with status & filter buttons |
| `/search` | Search orders by ID, name, phone, or email |
| `/export` | Download all orders as CSV (Excel-compatible) |
| `/products` | View product inventory with low-stock alerts |
| `/monitor` | Check website status (latency + status code) |
| `/monitor on` | Enable auto-monitoring (every 10 min) |
| `/monitor off` | Disable auto-monitoring |
| `/help` | Show command list |

**User Commands:**

| Command | Action |
| :--- | :--- |
| `/start` | Main menu with shopping options |
| `/menu` | Return to menu |
| `/track` | Track an order by ID |
| `/products` | Browse product catalog |
| `/about` | About Nongor Premium |
| `/contact` | Contact information & business hours |
| `/help` | Show command list |

### 🔄 Background Tasks
Three concurrent background tasks run automatically:

| Task | Interval | Purpose |
| :--- | :--- | :--- |
| **Website Monitor** | Every 5 min | Alerts admins if website goes down |
| **Daily Report** | 9:00 PM (BD Time) | Sends automated business performance report |
| **Order Polling** | Every 60 sec | Notifies admins of new orders in real-time |

---

## 🚀 Deployment (Fly.io)

We rely on **Fly.io** for production-grade hosting.

1.  **Install Fly CLI** and login.
2.  **Initialize**:
    ```bash
    fly launch
    ```
3.  **Set Secrets** (Crucial for security):
    ```bash
    fly secrets set TELEGRAM_BOT_TOKEN=... \
                    GEMINI_API_KEY=... \
                    DATABASE_URL=... \
                    ADMIN_USER_IDS=... \
                    WEBSITE_URL=...
    ```
4.  **Deploy**:
    ```bash
    fly deploy
    ```

---

## 📂 Project Structure

```
nongor_bot_v3/
├── bot_standard/
│   ├── main.py             # 🧠 The BRAIN. All bot logic, handlers & AI routing.
│   ├── database.py         # 💾 The MEMORY. Async PostgreSQL with connection pooling.
│   └── knowledge_base.md   # 📖 The RULEBOOK. Policies for Customer AI.
│
├── pages/
│   └── api/
│       └── analytics.js    # � Vercel API endpoint for Google Analytics 4.
│
├── schema.sql              # 🗄️ Full database schema (users, orders, products, coupons).
├── requirements.txt        # 📦 Python dependencies.
├── .env.example            # 🔑 Environment variable template.
├── Dockerfile              # 🐳 Container config for Fly.io.
├── fly.toml                # ✈️ Fly.io deployment config.
├── test.py                 # 🧪 Database connection test.
├── test_analytics.py       # 🧪 Full-stack analytics integration test.
└── README.md               # 📘 This manual.
```

---

<div align="center">

**© 2026 Nongor Brand Technology**
*Built for High-Growth E-commerce*

</div>
