"""
Neon Serverless PostgreSQL Adapter for Cloudflare Workers
Uses Neon's HTTP API via their serverless endpoint
"""
from js import fetch
import json
import logging

logger = logging.getLogger(__name__)

class Database:
    """
    Neon serverless database adapter using HTTP fetch.
    Connection string format: postgres://user:pass@host/dbname
    """
    
    def __init__(self, connection_string):
        """
        Parse Neon connection string and prepare for serverless queries.
        Format: postgres://user:password@ep-xxx.region.aws.neon.tech/dbname
        """
        # Parse connection string
        import re
        match = re.match(r'postgres://([^:]+):([^@]+)@([^/]+)/(.+)', connection_string)
        
        if not match:
            raise ValueError("Invalid Neon connection string format")
        
        user, password, host, database = match.groups()
        
        # Neon HTTP endpoint format
        self.endpoint = f"https://{host}"
        self.auth_header = self._create_auth_header(user, password)
        self.database = database
        self.user = user

    def _create_auth_header(self, user, password):
        """Create basic auth header for Neon HTTP requests"""
        import base64
        credentials = f"{user}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def _execute(self, query, params=None):
        """Execute SQL query using Neon's HTTP endpoint."""
        
        # Format parameters for PostgreSQL
        formatted_query = query
        if params:
            for i, param in enumerate(params, 1):
                placeholder = f"${i}"
                if isinstance(param, str):
                    value = f"'{param}'"
                elif param is None:
                    value = "NULL"
                else:
                    value = str(param)
                formatted_query = formatted_query.replace(placeholder, value, 1)
        
        try:
            response = await fetch(f"{self.endpoint}/sql", {
                "method": "POST",
                "headers": {
                    "Authorization": self.auth_header,
                    "Content-Type": "application/json",
                    "Neon-Connection-String": f"postgres://{self.user}@{self.endpoint.replace('https://', '')}/{self.database}"
                },
                "body": json.dumps({
                    "query": formatted_query,
                    "arrayMode": False
                })
            })
            
            if response.status != 200:
                logger.error(f"Database error: HTTP {response.status}")
                return None
            
            data = await response.json()
            
            # Format response
            if "rows" in data:
                return data["rows"]
            
            return data
            
        except Exception as e:
            logger.error(f"Database execution error: {e}")
            return None

    async def fetch_one(self, query, params=None):
        """Fetch single row"""
        results = await self._execute(query, params)
        if results and isinstance(results, list) and len(results) > 0:
            return results[0]
        return None

    async def fetch_all(self, query, params=None):
        """Fetch all rows"""
        results = await self._execute(query, params)
        return results if isinstance(results, list) else []

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
        return await self.fetch_all(query, [days, limit])

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
        return await self._execute(query, [user_id, username, first_name])
