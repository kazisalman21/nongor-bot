"""
AsyncPostgreSQL Database Adapter using asyncpg
Direct connection to Neon/Postgres
"""
import asyncpg
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class Database:
    """
    AsyncPostgreSQL database adapter.
    """
    
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.pool = None

    async def connect(self):
        """Initialize connection pool"""
        if not self.pool:
            try:
                # SSL is required for Neon
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                
                self.pool = await asyncpg.create_pool(
                    self.connection_string,
                    min_size=1,
                    max_size=5,
                    ssl=ctx
                )
                logger.info("Database connection pool established.")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise e

    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed.")

    async def fetch_one(self, query, params=None):
        """Fetch single row"""
        if not self.pool: await self.connect()
        try:
            async with self.pool.acquire() as connection:
                # asyncpg uses $1, $2, etc. natively
                if params:
                    row = await connection.fetchrow(query, *params)
                else:
                    row = await connection.fetchrow(query)
                return row
        except Exception as e:
            logger.error(f"DB Error (fetch_one): {e}")
            return None

    async def fetch_all(self, query, params=None):
        """Fetch all rows"""
        if not self.pool: await self.connect()
        try:
            async with self.pool.acquire() as connection:
                if params:
                    rows = await connection.fetch(query, *params)
                else:
                    rows = await connection.fetch(query)
                return rows
        except Exception as e:
            logger.error(f"DB Error (fetch_all): {e}")
            return []

    async def execute(self, query, params=None):
        """Execute a query (INSERT/UPDATE/DELETE)"""
        if not self.pool: await self.connect()
        try:
            async with self.pool.acquire() as connection:
                if params:
                    result = await connection.execute(query, *params)
                else:
                    result = await connection.execute(query)
                return result
        except Exception as e:
            logger.error(f"DB Error (execute): {e}")
            return None

    # =========================================
    # BUSINESS LOGIC METHODS
    # =========================================

    async def get_order_by_id(self, order_id):
        query = "SELECT * FROM orders WHERE id = $1"
        return await self.fetch_one(query, [order_id])

    async def get_order_by_phone(self, phone):
        query = "SELECT * FROM orders WHERE phone = $1 ORDER BY created_at DESC LIMIT 1"
        return await self.fetch_one(query, [phone])

    async def get_available_products(self):
        query = """
            SELECT 
                product_name as name, 
                MAX(COALESCE(price, total_price / NULLIF(quantity, 0), 0)) as price,
                COUNT(*) as order_count
            FROM orders
            WHERE product_name IS NOT NULL 
            GROUP BY product_name
            ORDER BY product_name
        """
        return await self.fetch_all(query)

    async def get_today_stats(self):
        query = """
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(COALESCE(total, total_price, 0)), 0) as total_revenue
            FROM orders 
            WHERE DATE(created_at) = CURRENT_DATE 
            AND status != 'cancelled'
        """
        result = await self.fetch_one(query)
        return result if result else {'order_count': 0, 'total_revenue': 0}

    async def get_weekly_stats(self):
        query = """
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(COALESCE(total, total_price, 0)), 0) as total_revenue,
                COALESCE(AVG(COALESCE(total, total_price, 0)), 0) as avg_order_value
            FROM orders 
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            AND status != 'cancelled'
        """
        result = await self.fetch_one(query)
        return result if result else {'order_count': 0, 'total_revenue': 0, 'avg_order_value': 0}

    async def get_top_products(self, days=30, limit=5):
        query = """
            SELECT 
                product_name, 
                COALESCE(SUM(COALESCE(total, total_price, 0)), 0) as revenue,
                COUNT(*) as order_count
            FROM orders
            WHERE created_at >= CURRENT_DATE - ($1 || ' days')::INTERVAL
            AND status != 'cancelled'
            AND product_name IS NOT NULL
            GROUP BY product_name 
            ORDER BY revenue DESC 
            LIMIT $2
        """
        return await self.fetch_all(query, [str(days), limit]) # Casting days to str for concatenation in SQL if needed, but parameter is $1

    async def get_recent_orders(self, limit=15):
        query = "SELECT id as order_id, customer_name, phone, product_name, total, status, created_at FROM orders ORDER BY created_at DESC LIMIT $1"
        return await self.fetch_all(query, [limit])

    async def get_products_for_context(self):
        """Get product info formatted for AI context"""
        products = await self.get_available_products()
        if not products:
            return "No products available"
        
        lines = ["AVAILABLE PRODUCTS:"]
        for p in products:
            price = p.get('price', 0) or 0
            lines.append(f"- {p['name']}: ৳{price:,.2f}")
        return "\n".join(lines)
    
    async def save_user(self, user_id, username, first_name=None):
        """Save or update user"""
        query = """
            INSERT INTO users (user_id, username, first_name, last_seen)
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) 
            DO UPDATE SET username = $2, first_name = $3, last_seen = CURRENT_TIMESTAMP
        """
        return await self.execute(query, [user_id, username, first_name])

    async def get_user_stats(self):
        """Get total and active user counts"""
        query = """
            SELECT 
                COUNT(*) as total_users,
                COUNT(*) FILTER (WHERE last_seen > CURRENT_DATE - INTERVAL '7 days') as active_users
            FROM users
        """
        res = await self.fetch_one(query)
        return res if res else {'total_users': 0, 'active_users': 0}

    async def get_all_orders(self):
        """Fetch all orders for CSV export"""
        query = "SELECT id as order_id, customer_name, phone, product_name, total, status, created_at FROM orders ORDER BY created_at DESC"
        return await self.fetch_all(query)

    async def get_latest_order_id(self):
        """Get the ID of the most recent order"""
        query = "SELECT id FROM orders ORDER BY id DESC LIMIT 1"
        res = await self.fetch_one(query)
        return res['id'] if res else 0

    async def get_daily_sales_stats(self, days=7):
        """Get daily sales totals for charts"""
        query = """
            SELECT 
                TO_CHAR(created_at, 'YYYY-MM-DD') as date,
                COALESCE(SUM(COALESCE(total, total_price, 0)), 0) as revenue
            FROM orders
            WHERE created_at >= CURRENT_DATE - ($1 || ' days')::INTERVAL
            AND status != 'cancelled'
            GROUP BY date
            ORDER BY date ASC
        """
        return await self.fetch_all(query, [str(days)])
