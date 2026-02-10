# REVISED Deployment Guide: Nongor Bot V3

## ⚠️ CRITICAL UPDATE: Cloudflare Workers Python (Beta)
Cloudflare Workers Python is still in Beta. If you experience unexpected database timeouts or "Module not found" errors, we strongly recommend **Option B (Fly.io)**.

---

## Option A: Cloudflare Workers (The Serverless Path)

### 1. Preparation
Ensure the file structure is correct. Each worker MUST have its own copy of `database.py`:
```text
/workers/bot/src/index.py
/workers/bot/src/database.py
/workers/reports/src/index.py
/workers/reports/src/database.py
```

### 2. Database Schema
Copy the contents of `schema.sql` and run them in the **Neon SQL Editor** on your dashboard.

### 3. Deploy
```bash
# Bot
cd workers/bot && wrangler deploy
# Monitor
cd ../monitor && wrangler deploy
# Reports
cd ../reports && wrangler deploy
```

### 4. Register Webhook
Replace `<TOKEN>` and `<URL>`:
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://nongor-bot.<your-subdomain>.workers.dev"
```

---

## Option B: Fly.io (The Stable Path - Recommended)

If you want to use your existing code with **zero changes** and standard PostgreSQL drivers (polling mode), use Fly.io.

### 1. Create a `Dockerfile` in the root:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "bot_v3_enhanced.py"]
```

### 2. Deploy
```bash
fly launch
fly secrets set $(cat .env | xargs)
fly deploy
```

---

## 🛠️ Troubleshooting
- **ModuleNotFoundError: database**: Ensure `database.py` is in the `src/` folder of the worker.
- **Database Timeouts**: Neon HTTP over Cloudflare Workers is experimental. If it persists, switch to Fly.io.
- **Button Crashes**: Fixed in the latest `index.py`. Ensure you deployed the corrected version.
