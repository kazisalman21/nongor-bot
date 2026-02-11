
"""
Enhanced AsyncPostgreSQL Database Adapter
Matches actual Nongor database schema with advanced features
"""
import asyncpg
import logging
import re
from urllib.parse import urlparse
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Database:
    """
    AsyncPostgreSQL database adapter with enhanced features.
    Matches actual Nongor schema: orders, products, order_items, coupons, users
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
        if not self.pool: 
            await self.connect()
        try:
            async with self.pool.acquire() as connection:
                if params:
                    row = await connection.fetchrow(query, *params)
                else:
                    row = await connection.fetchrow(query)
                return row
        except Exception as e:
            logger.error(f"DB Error (fetch_one): {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            return None

    async def fetch_all(self, query, params=None):
        """Fetch all rows"""
        if not self.pool: 
            await self.connect()
        try:
            async with self.pool.acquire() as connection:
                if params:
                    rows = await connection.fetch(query, *params)
                else:
                    rows = await connection.fetch(query)
                return rows
        except Exception as e:
            logger.error(f"DB Error (fetch_all): {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            return []

    async def execute(self, query, params=None):
        """Execute a query (INSERT/UPDATE/DELETE)"""
        if not self.pool: 
            await self.connect()
        try:
            async with self.pool.acquire() as connection:
                if params:
                    result = await connection.execute(query, *params)
                else:
                    result = await connection.execute(query)
                return result
        except Exception as e:
            logger.error(f"DB Error (execute): {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            return None

    # =========================================
    # ORDER MANAGEMENT
    # =========================================

    async def get_order_by_id(self, order_id):
        """Get order by numeric ID"""
        query = """
            SELECT 
                id,
                order_id,
                customer_name,
                phone,
                address,
                product_name,
                quantity,
                total_price,
                status,
                delivery_status,
                payment_status,
                payment_method,
                customer_email,
                coupon_code,
                discount_amount,
                tracking_token,
                trx_id,
                sender_number,
                delivery_date,
                created_at
            FROM orders 
            WHERE id = $1
        """
        return await self.fetch_one(query, [order_id])

    async def get_order_by_order_id(self, order_id_string):
        """Get order by order_id string (e.g., '#NG-63497')"""
        query = """
            SELECT 
                id,
                order_id,
                customer_name,
                phone,
                address,
                product_name,
                quantity,
                total_price,
                status,
                delivery_status,
                payment_status,
                payment_method,
                customer_email,
                coupon_code,
                discount_amount,
                tracking_token,
                trx_id,
                sender_number,
                delivery_date,
                created_at
            FROM orders 
            WHERE order_id = $1
        """
        return await self.fetch_one(query, [order_id_string])

    async def get_order_by_phone(self, phone):
        """Get most recent order for a phone number"""
        query = """
            SELECT 
                id,
                order_id,
                customer_name,
                phone,
                address,
                product_name,
                quantity,
                total_price,
                status,
                delivery_status,
                payment_status,
                payment_method,
                customer_email,
                coupon_code,
                discount_amount,
                tracking_token,
                delivery_date,
                created_at
            FROM orders 
            WHERE phone = $1 
            ORDER BY created_at DESC 
            LIMIT 1
        """
        return await self.fetch_one(query, [phone])

    async def search_orders(self, search_term):
        """Search orders by order_id, customer name, phone, or email"""
        query = """
            SELECT 
                id,
                order_id,
                customer_name,
                phone,
                total_price,
                status,
                delivery_status,
                payment_status,
                created_at
            FROM orders
            WHERE 
                order_id ILIKE $1
                OR customer_name ILIKE $1
                OR phone ILIKE $1
                OR customer_email ILIKE $1
            ORDER BY created_at DESC
            LIMIT 20
        """
        pattern = f"%{search_term}%"
        return await self.fetch_all(query, [pattern])

    async def get_orders_by_status(self, status, limit=50):
        """Get orders filtered by status"""
        query = """
            SELECT 
                id,
                order_id,
                customer_name,
                phone,
                total_price,
                status,
                delivery_status,
                payment_status,
                created_at
            FROM orders
            WHERE status = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        return await self.fetch_all(query, [status, limit])

    async def get_orders_by_date_range(self, start_date, end_date, limit=100):
        """Get orders within a date range"""
        query = """
            SELECT 
                id,
                order_id,
                customer_name,
                phone,
                total_price,
                status,
                delivery_status,
                payment_status,
                created_at
            FROM orders
            WHERE created_at >= $1 AND created_at <= $2
            ORDER BY created_at DESC
            LIMIT $3
        """
        return await self.fetch_all(query, [start_date, end_date, limit])

    async def get_recent_orders(self, limit=15):
        """Get recent orders with essential fields"""
        query = """
            SELECT 
                id,
                order_id,
                customer_name,
                phone,
                product_name,
                total_price,
                status,
                delivery_status,
                payment_status,
                created_at
            FROM orders 
            ORDER BY created_at DESC 
            LIMIT $1
        """
        return await self.fetch_all(query, [limit])

    async def get_all_orders(self):
        """Fetch all orders for CSV export"""
        query = """
            SELECT 
                id,
                order_id,
                customer_name,
                phone,
                product_name,
                quantity,
                total_price,
                status,
                delivery_status,
                payment_status,
                payment_method,
                coupon_code,
                discount_amount,
                created_at
            FROM orders 
            ORDER BY created_at DESC
        """
        return await self.fetch_all(query)

    async def get_latest_order_id(self):
        """Get the ID of the most recent order"""
        query = "SELECT id FROM orders ORDER BY id DESC LIMIT 1"
        res = await self.fetch_one(query)
        return res['id'] if res else 0

    async def update_order_status(self, order_id, status, delivery_status=None):
        """Update order status"""
        if delivery_status:
            query = """
                UPDATE orders 
                SET status = $1, delivery_status = $2 
                WHERE id = $3
            """
            return await self.execute(query, [status, delivery_status, order_id])
        else:
            query = "UPDATE orders SET status = $1 WHERE id = $2"
            return await self.execute(query, [status, order_id])

    async def add_tracking_info(self, order_id, tracking_token, courier_name=None):
        """Add tracking information to order"""
        query = """
            UPDATE orders 
            SET tracking_token = $1
            WHERE id = $2
        """
        return await self.execute(query, [tracking_token, order_id])

    # =========================================
    # PRODUCT MANAGEMENT
    # =========================================

    async def get_all_products(self, active_only=True):
        """Get all products"""
        if active_only:
            query = """
                SELECT 
                    id,
                    name,
                    description,
                    price,
                    stock_quantity,
                    category_name,
                    is_featured,
                    image,
                    images
                FROM products
                WHERE is_active = TRUE
                ORDER BY name
            """
        else:
            query = """
                SELECT 
                    id,
                    name,
                    description,
                    price,
                    stock_quantity,
                    category_name,
                    is_featured,
                    is_active,
                    image,
                    images
                FROM products
                ORDER BY name
            """
        return await self.fetch_all(query)

    async def search_products(self, search_term):
        """Search products by name or category"""
        query = """
            SELECT 
                id,
                name,
                description,
                price,
                stock_quantity,
                category_name,
                is_featured,
                image
            FROM products
            WHERE is_active = TRUE
            AND (
                name ILIKE $1
                OR description ILIKE $1
                OR category_name ILIKE $1
            )
            ORDER BY is_featured DESC, name
            LIMIT 20
        """
        pattern = f"%{search_term}%"
        return await self.fetch_all(query, [pattern])

    async def get_product_by_id(self, product_id):
        """Get product details by ID"""
        query = """
            SELECT 
                id,
                name,
                description,
                price,
                stock_quantity,
                category_name,
                is_featured,
                is_active,
                image,
                images,
                created_at,
                updated_at
            FROM products
            WHERE id = $1
        """
        return await self.fetch_one(query, [product_id])

    async def get_low_stock_products(self, threshold=10):
        """Get products with low stock"""
        query = """
            SELECT 
                id,
                name,
                price,
                stock_quantity,
                category_name
            FROM products
            WHERE is_active = TRUE 
            AND stock_quantity < $1
            ORDER BY stock_quantity ASC
        """
        return await self.fetch_all(query, [threshold])

    async def get_featured_products(self, limit=10):
        """Get featured products"""
        query = """
            SELECT 
                id,
                name,
                description,
                price,
                stock_quantity,
                category_name,
                image
            FROM products
            WHERE is_active = TRUE AND is_featured = TRUE
            ORDER BY created_at DESC
            LIMIT $1
        """
        return await self.fetch_all(query, [limit])

    async def get_products_for_context(self):
        """Get product info formatted for AI context"""
        products = await self.get_all_products()
        if not products:
            return "No products available"
        
        lines = ["AVAILABLE PRODUCTS:"]
        for p in products:
            price = p.get('price', 0) or 0
            stock = p.get('stock_quantity', 0)
            category = p.get('category_name', 'General')
            stock_status = f"({stock} in stock)" if stock > 0 else "(Out of stock)"
            lines.append(f"- {p['name']}: ৳{price:,.2f} {stock_status} - {category}")
        return "\n".join(lines)

    # =========================================
    # COUPON MANAGEMENT
    # =========================================

    async def get_all_coupons(self, active_only=True):
        """Get all coupons"""
        if active_only:
            query = """
                SELECT 
                    id,
                    code,
                    discount_type,
                    discount_value,
                    min_order_value as min_order_amount,
                    max_discount_amount as max_discount,
                    usage_limit,
                    usage_count as used_count,
                    created_at as valid_from,
                    expires_at as valid_until,
                    is_active
                FROM coupons
                WHERE is_active = TRUE
                ORDER BY created_at DESC
            """
            return await self.fetch_all(query)
        else:
            query = """
                SELECT 
                    id,
                    code,
                    discount_type,
                    discount_value,
                    min_order_value as min_order_amount,
                    max_discount_amount as max_discount,
                    usage_limit,
                    usage_count as used_count,
                    created_at as valid_from,
                    expires_at as valid_until,
                    is_active
                FROM coupons
                ORDER BY created_at DESC
            """
            return await self.fetch_all(query)

    async def get_coupon_by_code(self, code):
        """Get coupon details by code"""
        query = """
            SELECT 
                id,
                code,
                discount_type,
                discount_value,
                min_order_value as min_order_amount,
                max_discount_amount as max_discount,
                usage_limit,
                usage_count as used_count,
                created_at as valid_from,
                expires_at as valid_until,
                is_active
            FROM coupons
            WHERE code = $1
        """
        return await self.fetch_one(query, [code.upper()])

    async def validate_coupon(self, code, order_amount):
        """Validate if a coupon can be used"""
        coupon = await self.get_coupon_by_code(code)
        
        if not coupon:
            return {"valid": False, "message": "Coupon not found"}
        
        if not coupon['is_active']:
            return {"valid": False, "message": "Coupon is inactive"}
        
        now = datetime.now()
        
        # Check validity dates
        # Note: valid_from is aliased to created_at, so it's always valid from creation
        if coupon['valid_until'] and now > coupon['valid_until']:
            return {"valid": False, "message": "Coupon has expired"}
        
        # Check usage limit
        if coupon['usage_limit'] and coupon['used_count'] >= coupon['usage_limit']:
            return {"valid": False, "message": "Coupon usage limit reached"}
        
        # Check minimum order amount
        if coupon['min_order_amount'] and order_amount < coupon['min_order_amount']:
            return {
                "valid": False, 
                "message": f"Minimum order amount is ৳{coupon['min_order_amount']}"
            }
        
        # Calculate discount
        if coupon['discount_type'] == 'percentage':
            discount = (order_amount * coupon['discount_value']) / 100
            if coupon['max_discount']:
                discount = min(discount, coupon['max_discount'])
        else:  # fixed
            discount = coupon['discount_value']
        
        return {
            "valid": True,
            "discount": discount,
            "coupon": coupon
        }

    # =========================================
    # ANALYTICS & REPORTS
    # =========================================

    async def get_today_stats(self):
        """Get today's sales statistics"""
        query = """
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(total_price), 0) as total_revenue,
                COALESCE(AVG(total_price), 0) as avg_order_value
            FROM orders 
            WHERE DATE(created_at) = CURRENT_DATE 
            AND status != 'Cancelled'
        """
        result = await self.fetch_one(query)
        return result if result else {
            'order_count': 0, 
            'total_revenue': 0,
            'avg_order_value': 0
        }

    async def get_weekly_stats(self):
        """Get weekly sales statistics"""
        query = """
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(total_price), 0) as total_revenue,
                COALESCE(AVG(total_price), 0) as avg_order_value
            FROM orders 
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            AND status != 'Cancelled'
        """
        result = await self.fetch_one(query)
        return result if result else {
            'order_count': 0, 
            'total_revenue': 0, 
            'avg_order_value': 0
        }

    async def get_monthly_stats(self):
        """Get monthly sales statistics"""
        query = """
            SELECT 
                COUNT(*) as order_count,
                COALESCE(SUM(total_price), 0) as total_revenue,
                COALESCE(AVG(total_price), 0) as avg_order_value
            FROM orders 
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            AND status != 'Cancelled'
        """
        result = await self.fetch_one(query)
        return result if result else {
            'order_count': 0, 
            'total_revenue': 0, 
            'avg_order_value': 0
        }

    async def get_top_products(self, days=30, limit=5):
        """Get top selling products by revenue"""
        query = """
            SELECT 
                product_name,
                COUNT(*) as order_count,
                SUM(quantity) as total_quantity,
                COALESCE(SUM(total_price), 0) as revenue
            FROM orders
            WHERE created_at >= CURRENT_DATE - $1 * INTERVAL '1 day'
            AND status != 'Cancelled'
            AND product_name IS NOT NULL
            GROUP BY product_name 
            ORDER BY revenue DESC 
            LIMIT $2
        """
        return await self.fetch_all(query, [days, limit])

    async def get_daily_sales_stats(self, days=7):
        """Get daily sales totals for charts"""
        query = """
            SELECT 
                TO_CHAR(created_at, 'YYYY-MM-DD') as date,
                COUNT(*) as order_count,
                COALESCE(SUM(total_price), 0) as revenue
            FROM orders
            WHERE created_at >= CURRENT_DATE - $1 * INTERVAL '1 day'
            AND status != 'Cancelled'
            GROUP BY date
            ORDER BY date ASC
        """
        return await self.fetch_all(query, [days])

    async def get_status_breakdown(self):
        """Get order count by status"""
        query = """
            SELECT 
                status,
                COUNT(*) as count,
                COALESCE(SUM(total_price), 0) as revenue
            FROM orders
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY status
            ORDER BY count DESC
        """
        return await self.fetch_all(query)

    async def get_payment_method_stats(self):
        """Get payment method statistics"""
        query = """
            SELECT 
                payment_method,
                COUNT(*) as count,
                COALESCE(SUM(total_price), 0) as revenue
            FROM orders
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            AND status != 'Cancelled'
            GROUP BY payment_method
            ORDER BY count DESC
        """
        return await self.fetch_all(query)

    async def get_delivery_status_breakdown(self):
        """Get delivery status breakdown"""
        query = """
            SELECT 
                delivery_status,
                COUNT(*) as count
            FROM orders
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY delivery_status
            ORDER BY count DESC
        """
        return await self.fetch_all(query)

    # =========================================
    # USER MANAGEMENT
    # =========================================
    
    async def save_user(self, user_id, username, first_name=None):
        """Save or update user"""
        query = """
            INSERT INTO users (user_id, username, first_name, last_seen)
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                username = $2, 
                first_name = $3, 
                last_seen = CURRENT_TIMESTAMP
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

    async def get_customer_order_history(self, phone):
        """Get order history for a customer by phone"""
        query = """
            SELECT 
                id,
                order_id,
                product_name,
                total_price,
                status,
                delivery_status,
                payment_status,
                created_at
            FROM orders
            WHERE phone = $1
            ORDER BY created_at DESC
        """
        return await self.fetch_all(query, [phone])

    # =========================================
    # ADMIN UTILITIES
    # =========================================

    async def get_inventory_alerts(self):
        """Get low stock and out of stock products"""
        query = """
            SELECT 
                id,
                name,
                stock_quantity,
                category_name,
                price
            FROM products
            WHERE is_active = TRUE 
            AND stock_quantity <= 10
            ORDER BY stock_quantity ASC
        """
        return await self.fetch_all(query)

    async def get_pending_orders_count(self):
        """Get count of pending orders"""
        query = """
            SELECT COUNT(*) as count
            FROM orders
            WHERE status = 'Pending' OR delivery_status = 'Pending'
        """
        result = await self.fetch_one(query)
        return result['count'] if result else 0

    async def get_revenue_by_category(self, days=30):
        """Get revenue breakdown by product category"""
        query = """
            SELECT 
                p.category_name,
                COUNT(o.id) as order_count,
                COALESCE(SUM(o.total_price), 0) as revenue
            FROM orders o
            JOIN products p ON o.product_name ILIKE '%' || p.name || '%'
            WHERE o.created_at >= CURRENT_DATE - $1 * INTERVAL '1 day'
            AND o.status != 'Cancelled'
            GROUP BY p.category_name
            ORDER BY revenue DESC
        """
        return await self.fetch_all(query, [days])
