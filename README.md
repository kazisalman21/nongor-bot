# 🚢 Nongor Premium Bot v4.0 (AI-Powered)

<div align="center">

![Nongor Bot Banner](https://img.shields.io/badge/Nongor-Premium_Bot-2CA5E0?style=for-the-badge&logo=probot&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)
![AI](https://img.shields.io/badge/AI-Gemini_2.5_Flash-8E75B2?style=for-the-badge&logo=google&logoColor=white)
![Database](https://img.shields.io/badge/DB-PostgreSQL_Neon-336791?style=for-the-badge&logo=postgresql&logoColor=white)

**The Ultimate Intelligence System for E-commerce**
*Dual-Persona AI • Strategic Business Analyst • Sales Conversion Expert*

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

### 📊 Real-Time Business Dashboard
Forget spreadsheets. Ask the Admin AI _"How is business today?"_ and get:
- **Revenue Snapshot**: Today vs. Last Week vs. Last Month.
- **Inventory Alerts**: ⚠️ Warnings for low-stock items that are selling fast.
- **Top Performers**: ⭐ Which products are driving your revenue exactly.
- **Category Analysis**: 📈 Which collection (Panjabi, Saree, etc.) is trending.

---

## 🏗️ Technical Architecture

This project is built for **scale** and **reliability**.

```mermaid
graph TD
    User[User/Customer] -->|Telegram| Bot[Nongor Bot v4]
    Admin[Admin Owner] -->|Telegram| Bot
    
    subgraph "Core Intelligence"
        Bot -->|Route: Customer| SalesAI[Lead Sales AI]
        Bot -->|Route: Admin| BizAI[Senior Business AI]
    end
    
    subgraph "Data Layer"
        SalesAI -- Read Only --> KB[Knowledge Base.md]
        BizAI -- Read/Write --> DB[(PostgreSQL Neon)]
        Bot -- AsyncPG --> DB
    end
    
    subgraph "External"
        SalesAI --> Gemini[Google Gemini 2.5 Flash]
        BizAI --> Gemini
    end
```

### Key Technologies
- **Python 3.12+**: Asynchronous core using `python-telegram-bot`.
- **AsyncPG**: High-performance non-blocking database driver.
- **Google Gemini 2.5 Flash**: Fast, low-latency LLM for instant replies.
- **Matplotlib**: Generates beautiful sales charts on the fly.
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

### 3. Configuration (.env)
Fill in your credentials in `.env`:
```ini
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
ADMIN_USER_IDS=987654321,123456789 (comma separated)
GEMINI_API_KEY=AIzaSy...
NETLIFY_DATABASE_URL=postgresql://user:pass@ep-xyz.region.neon.tech/neondb?sslmode=require
```

### 4. Run the Bot
```bash
python bot_standard/main.py
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
| Command | Action |
| :--- | :--- |
| `/start` | Open the Main Menu |
| `/refresh` | Force sync data from database |
| `/dashboard` | View quick visuals of today's stats |
| `/orders` | See last 10 orders with status buttons |
| `/products` | Manage inventory context |

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
                    NETLIFY_DATABASE_URL=...
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
│   ├── main.py             # 🧠 The BRAIN. Contains all logic & AI.
│   ├── database.py         # 💾 The MEMORY. Async database methods.
│   ├── knowledge_base.md   # 📖 The RULEBOOK. Policies for Customer AI.
│   └── backups/            # 📦 Old files (safe to ignore)
│
├── requirements.txt        # Python libraries
├── fly.toml                # Deployment config
└── README.md               # This manual
```

---

<div align="center">

**© 2026 Nongor Brand Technology**
*Built for High-Growth E-commerce*

</div>
