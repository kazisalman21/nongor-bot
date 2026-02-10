"""
Nongor Bot V3 - Enhanced Database Connector
PostgreSQL database interface with comprehensive query methods
"""

import os
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager

import pg8000
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class Database:
    """
    Enhanced database connector with connection pooling and 
    comprehensive query methods for the Nongor e-commerce bot.
    """
    
    def __init__(self):
        """Initialize database connection parameters"""
        self.connection_string = os.getenv('NETLIFY_DATABASE_URL')
        if not self.connection_string:
            raise ValueError("NETLIFY_DATABASE_URL environment variable not set")
        
        self._connection = None
        self._parse_connection_string()
    
    def _parse_connection_string(self):
        """Parse PostgreSQL connection string"""
        # Format: postgresql://user:password@host:port/database?sslmode=require
        url = self.connection_string
        
        # Remove protocol
        if url.startswith('postgresql://'):
            url = url[13:]
        elif url.startswith('postgres://'):
            url = url[11:]
        
        # Split user:pass@host:port/database
        auth_host, db_params = url.split('@', 1)
        
        # Get user and password
        if ':' in auth_host:
            self.user, self.password = auth_host.split(':', 1)
        else:
            self.user = auth_host
            self.password = ''
        
        # Get host, port, database
        host_port, db_name = db_params.split('/', 1)
        
        if ':' in host_port:
            self.host, port_str = host_port.split(':', 1)
            self.port = int(port_str.split('?')[0])  # Remove query params
        else:
            self.host = host_port
            self.port = 5432
        
        # Database name (remove query params)
        self.database = db_name.split('?')[0]
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup"""
        conn = None
        try:
            conn = pg8000.connect(
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                database=self.database,
                ssl_context=True
            )
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Execute query and fetch single result"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                row = cursor.fetchone()
                
                if row:
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            logger.error(f"Query error: {e}")
            return None
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute query and fetch all results"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Query error: {e}")
            return []
    
    def execute(self, query: str, params: tuple = ()) -> bool:
        """Execute query without returning results"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Execute error: {e}")
            return False
    
    # =========================================
    # ORDER QUERIES
    # =========================================
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """Get specific order by ID"""
        query = """
            SELECT *
            FROM orders o
            WHERE o.order_id = %s OR o.id = %s
            LIMIT 1
        """
        return self.fetch_one(query, (str(order_id), order_id))
    
    def get_order_by_phone(self, phone: str) -> Optional[Dict]:
        """Get latest order by phone number"""
        # Normalize phone number
        phone = phone.replace(' ', '').replace('-', '').replace('+88', '')
        if not phone.startswith('0'):
            phone = '0' + phone
        
        query = """
            SELECT *
            FROM orders 
            WHERE phone LIKE %s
            ORDER BY created_at DESC 
            LIMIT 1
        """
        # Try exact match first, then pattern
        result = self.fetch_one(query, (f"%{phone[-10:]}",))
        return result
    
    def get_all_user_orders(self, phone: str, limit: int = 10) -> List[Dict]:
        """Get all orders for a phone number"""
        phone = phone.replace(' ', '').replace('-', '').replace('+88', '')
        
        query = """
            SELECT *
            FROM orders 
            WHERE phone LIKE %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        return self.fetch_all(query, (f"%{phone[-10:]}", limit))
    
    def get_recent_orders(self, limit: int = 15) -> List[Dict]:
        """Get most recent orders"""
        query = """
            SELECT 
                order_id, customer_name, phone,
                COALESCE(NULLIF(total, 0), total_price, 0) as total, status, payment_status, payment_method,
                created_at
            FROM orders 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        return self.fetch_all(query, (limit,))
    
    def get_orders_by_status(self, status: str, limit: int = 20) -> List[Dict]:
        """Get orders filtered by status"""
        query = """
            SELECT *
            FROM orders 
            WHERE status = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        return self.fetch_all(query, (status, limit))
    
    def get_order_count_by_status(self) -> Dict[str, int]:
        """Get count of orders grouped by status"""
        query = """
            SELECT status, COUNT(*) as count
            FROM orders
            GROUP BY status
        """
        results = self.fetch_all(query)
        return {r['status']: r['count'] for r in results}
    
    # =========================================
    # PRODUCT QUERIES
    # =========================================
    
    def get_available_products(self) -> List[Dict]:
        """Get available products derived from orders"""
        query = """
            SELECT 
                product_name as name, 
                MAX(COALESCE(price, total_price / NULLIF(quantity, 0), total_price, 0)) as price,
                COUNT(*) as order_count,
                'in_stock' as availability
            FROM orders
            WHERE product_name IS NOT NULL AND product_name != ''
            GROUP BY product_name
            ORDER BY product_name
        """
        return self.fetch_all(query)
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Get product by ID (from orders)"""
        query = """
            SELECT id, product_name as name, price, size, quantity
            FROM orders 
            WHERE id = %s
        """
        return self.fetch_one(query, (product_id,))
    
    def search_products(self, search_term: str) -> List[Dict]:
        """Search products by name"""
        query = """
            SELECT 
                product_name as name, 
                MAX(price) as price,
                COUNT(*) as order_count
            FROM orders 
            WHERE product_name ILIKE %s
            AND product_name IS NOT NULL
            GROUP BY product_name
            ORDER BY order_count DESC
        """
        pattern = f"%{search_term}%"
        return self.fetch_all(query, (pattern,))
    
    def get_low_stock_items(self, threshold: int = 10) -> List[Dict]:
        """No dedicated products table - returns empty list"""
        return []
    
    def get_out_of_stock_items(self) -> List[Dict]:
        """No dedicated products table - returns empty list"""
        return []
    
    def get_total_inventory(self) -> Dict:
        """Get inventory overview derived from orders"""
        query = """
            SELECT 
                COUNT(DISTINCT product_name) as total_products,
                COALESCE(SUM(quantity), 0) as total_units,
                0 as out_of_stock,
                0 as low_stock,
                COUNT(DISTINCT product_name) as well_stocked
            FROM orders
            WHERE product_name IS NOT NULL
        """
        return self.fetch_one(query) or {}
    
    # =========================================
    # ANALYTICS QUERIES
    # =========================================
    
    def get_today_stats(self) -> Dict:
        """Get today's statistics"""
        query = """
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(COALESCE(NULLIF(total, 0), total_price, 0)), 0) as total_revenue,
                COALESCE(AVG(COALESCE(NULLIF(total, 0), total_price, 0)), 0) as avg_order_value
            FROM orders 
            WHERE DATE(created_at) = CURRENT_DATE
            AND status != 'cancelled'
        """
        return self.fetch_one(query) or {'order_count': 0, 'total_revenue': 0, 'avg_order_value': 0}
    
    def get_weekly_stats(self) -> Dict:
        """Get this week's statistics"""
        query = """
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(COALESCE(NULLIF(total, 0), total_price, 0)), 0) as total_revenue,
                COALESCE(AVG(COALESCE(NULLIF(total, 0), total_price, 0)), 0) as avg_order_value
            FROM orders 
            WHERE created_at >= NOW() - (INTERVAL '1 day' * 7)
            AND status != 'cancelled'
        """
        return self.fetch_one(query) or {'order_count': 0, 'total_revenue': 0, 'avg_order_value': 0}
    
    def get_monthly_stats(self) -> Dict:
        """Get this month's statistics"""
        query = """
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(COALESCE(NULLIF(total, 0), total_price, 0)), 0) as total_revenue,
                COALESCE(AVG(COALESCE(NULLIF(total, 0), total_price, 0)), 0) as avg_order_value
            FROM orders 
            WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)
            AND status != 'cancelled'
        """
        return self.fetch_one(query) or {'order_count': 0, 'total_revenue': 0, 'avg_order_value': 0}
    
    def get_top_products(self, days: int = 30, limit: int = 5) -> List[Dict]:
        """Get top selling products by revenue"""
        query = """
            SELECT 
                product_name, 
                COALESCE(SUM(COALESCE(price * quantity, total_price, total, 0)), 0) as revenue,
                COUNT(*) as order_count,
                COALESCE(SUM(quantity), 0) as units_sold
            FROM orders
            WHERE created_at >= NOW() - (INTERVAL '1 day' * %s)
            AND status != 'cancelled'
            AND product_name IS NOT NULL
            GROUP BY product_name 
            ORDER BY revenue DESC 
            LIMIT %s
        """
        return self.fetch_all(query, (days, limit))
    
    def get_daily_revenue(self, days: int = 7) -> List[Dict]:
        """Get daily revenue for the last N days"""
        query = """
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as order_count,
                COALESCE(SUM(COALESCE(NULLIF(total, 0), total_price, 0)), 0) as revenue
            FROM orders
            WHERE created_at >= NOW() - (INTERVAL '1 day' * %s)
            AND status != 'cancelled'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """
        return self.fetch_all(query, (days,))
    
    # =========================================
    # USER STATISTICS
    # =========================================
    
    def get_unique_customers(self, days: int = 30) -> int:
        """Get count of unique customers"""
        query = """
            SELECT COUNT(DISTINCT phone) as count
            FROM orders
            WHERE created_at >= NOW() - (INTERVAL '1 day' * %s)
        """
        result = self.fetch_one(query, (days,))
        return result['count'] if result else 0
    
    def get_repeat_customers(self, days: int = 30) -> int:
        """Get count of repeat customers"""
        query = """
            SELECT COUNT(*) as count
            FROM (
                SELECT phone
                FROM orders
                WHERE created_at >= NOW() - (INTERVAL '1 day' * %s)
                GROUP BY phone
                HAVING COUNT(*) > 1
            ) repeat
        """
        result = self.fetch_one(query, (days,))
        return result['count'] if result else 0
    
    # =========================================
    # AI CONTEXT HELPERS
    # =========================================
    
    def get_products_for_context(self) -> str:
        """Get product list formatted for AI context"""
        products = self.get_available_products()
        
        lines = ["AVAILABLE PRODUCTS:"]
        for p in products:
            price = p.get('price', 0) or 0
            lines.append(f"- {p['name']}: ৳{price:,.2f}, {p.get('order_count', 0)} orders")
        
        return "\n".join(lines)
    
    def get_stats_for_context(self) -> str:
        """Get business stats formatted for AI context"""
        today = self.get_today_stats()
        weekly = self.get_weekly_stats()
        
        return f"""
TODAY'S BUSINESS:
- Total Orders: {today['order_count']}
- Revenue: ৳{today['total_revenue']:,.2f}

THIS WEEK:
- Total Orders: {weekly['order_count']}
- Revenue: ৳{weekly['total_revenue']:,.2f}
- Average Order: ৳{weekly['avg_order_value']:,.2f}
"""
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            result = self.fetch_one("SELECT 1 as test")
            return result is not None and result.get('test') == 1
        except:
            return False


# Singleton instance
_db_instance = None

def get_database() -> Database:
    """Get singleton database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
