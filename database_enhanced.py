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
            SELECT 
                o.*,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'product_name', oi.product_name,
                            'size', oi.size,
                            'quantity', oi.quantity,
                            'price', oi.price
                        )
                    ) FILTER (WHERE oi.id IS NOT NULL),
                    '[]'::json
                ) as items
            FROM orders o
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.order_id = %s OR o.id = %s
            GROUP BY o.id
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
            WHERE customer_phone LIKE %s
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
            WHERE customer_phone LIKE %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        return self.fetch_all(query, (f"%{phone[-10:]}", limit))
    
    def get_recent_orders(self, limit: int = 15) -> List[Dict]:
        """Get most recent orders"""
        query = """
            SELECT 
                order_id, customer_name, customer_phone,
                total, status, payment_status, payment_method,
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
        """Get all in-stock products"""
        query = """
            SELECT 
                id, name, price, stock_quantity, category,
                CASE 
                    WHEN stock_quantity = 0 THEN 'out_of_stock'
                    WHEN stock_quantity < 10 THEN 'low_stock'
                    ELSE 'in_stock'
                END as availability
            FROM products 
            WHERE is_active = true
            ORDER BY name
        """
        return self.fetch_all(query)
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Get product by ID"""
        query = """
            SELECT *
            FROM products 
            WHERE id = %s
        """
        return self.fetch_one(query, (product_id,))
    
    def search_products(self, search_term: str) -> List[Dict]:
        """Search products by name or category"""
        query = """
            SELECT id, name, description, price, stock_quantity, category
            FROM products 
            WHERE (name ILIKE %s OR category ILIKE %s)
            AND is_active = true
            AND stock_quantity > 0
            ORDER BY stock_quantity DESC
        """
        pattern = f"%{search_term}%"
        return self.fetch_all(query, (pattern, pattern))
    
    def get_low_stock_items(self, threshold: int = 10) -> List[Dict]:
        """Get products with low stock"""
        query = """
            SELECT id, name, stock_quantity, price
            FROM products 
            WHERE stock_quantity > 0 
            AND stock_quantity <= %s
            AND is_active = true
            ORDER BY stock_quantity ASC
        """
        return self.fetch_all(query, (threshold,))
    
    def get_out_of_stock_items(self) -> List[Dict]:
        """Get out of stock products"""
        query = """
            SELECT id, name, price
            FROM products 
            WHERE stock_quantity = 0
            AND is_active = true
            ORDER BY name
        """
        return self.fetch_all(query)
    
    def get_total_inventory(self) -> Dict:
        """Get total inventory overview"""
        query = """
            SELECT 
                COUNT(*) as total_products,
                COALESCE(SUM(stock_quantity), 0) as total_units,
                COUNT(CASE WHEN stock_quantity = 0 THEN 1 END) as out_of_stock,
                COUNT(CASE WHEN stock_quantity > 0 AND stock_quantity <= 10 THEN 1 END) as low_stock,
                COUNT(CASE WHEN stock_quantity > 10 THEN 1 END) as well_stocked
            FROM products
            WHERE is_active = true
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
                COALESCE(SUM(total), 0) as total_revenue,
                COALESCE(AVG(total), 0) as avg_order_value
            FROM orders 
            WHERE DATE(created_at) = CURRENT_DATE
        """
        return self.fetch_one(query) or {'order_count': 0, 'total_revenue': 0, 'avg_order_value': 0}
    
    def get_weekly_stats(self) -> Dict:
        """Get this week's statistics"""
        query = """
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(total), 0) as total_revenue,
                COALESCE(AVG(total), 0) as avg_order_value
            FROM orders 
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """
        return self.fetch_one(query) or {'order_count': 0, 'total_revenue': 0, 'avg_order_value': 0}
    
    def get_monthly_stats(self) -> Dict:
        """Get this month's statistics"""
        query = """
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(total), 0) as total_revenue,
                COALESCE(AVG(total), 0) as avg_order_value
            FROM orders 
            WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)
        """
        return self.fetch_one(query) or {'order_count': 0, 'total_revenue': 0, 'avg_order_value': 0}
    
    def get_top_products(self, days: int = 30, limit: int = 5) -> List[Dict]:
        """Get top selling products by revenue"""
        query = """
            SELECT 
                oi.product_name, 
                COALESCE(SUM(oi.price * oi.quantity), 0) as revenue,
                COUNT(DISTINCT o.id) as order_count,
                COALESCE(SUM(oi.quantity), 0) as units_sold
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.created_at >= NOW() - INTERVAL '%s days'
            GROUP BY oi.product_name 
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
                COALESCE(SUM(total), 0) as revenue
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '%s days'
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
            SELECT COUNT(DISTINCT customer_phone) as count
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '%s days'
        """
        result = self.fetch_one(query, (days,))
        return result['count'] if result else 0
    
    def get_repeat_customers(self, days: int = 30) -> int:
        """Get count of repeat customers"""
        query = """
            SELECT COUNT(*) as count
            FROM (
                SELECT customer_phone
                FROM orders
                WHERE created_at >= NOW() - INTERVAL '%s days'
                GROUP BY customer_phone
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
            stock_emoji = "✅" if p['availability'] == 'in_stock' else "⚠️" if p['availability'] == 'low_stock' else "❌"
            stock_text = f"{p['stock_quantity']} units" if p['stock_quantity'] > 0 else "Out of Stock"
            lines.append(f"- {p['name']}: {stock_emoji} {stock_text}, ৳{p['price']}")
        
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
