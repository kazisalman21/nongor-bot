"""
Nongor Bot V3 - Customer CRM System
Track customer purchase history, VIP status, loyalty points, and preferences.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CustomerCRM:
    """Customer relationship management for Nongor."""

    VIP_THRESHOLD = 5000   # BDT spent to become VIP
    GOLD_THRESHOLD = 15000  # BDT spent to become Gold

    def __init__(self):
        self.db = None
        self.cache: Dict[str, Dict] = {}  # phone -> profile cache

    def set_database(self, db):
        self.db = db

    def get_customer_profile(self, phone: str) -> Dict:
        """Build comprehensive customer profile from order history."""
        if not self.db:
            return {'error': 'Database not connected'}

        # Check cache (5 min TTL)
        cached = self.cache.get(phone)
        if cached and (datetime.now() - cached.get('_cached_at', datetime.min)).seconds < 300:
            return cached

        try:
            # Get all orders for this customer
            orders = self.db.fetch_all(
                "SELECT * FROM orders WHERE phone = %s ORDER BY created_at DESC",
                (phone,)
            ) or []

            if not orders:
                return {'found': False, 'phone': phone}

            # Calculate metrics
            total_spent = sum(float(o.get('total') or o.get('total_price') or 0) for o in orders)
            total_orders = len(orders)
            avg_order = total_spent / total_orders if total_orders > 0 else 0

            # Find favorite product
            product_counts = {}
            for o in orders:
                name = o.get('product_name', 'Unknown')
                product_counts[name] = product_counts.get(name, 0) + 1
            favorite = max(product_counts, key=product_counts.get) if product_counts else 'N/A'

            # Find favorite size
            size_counts = {}
            for o in orders:
                size = o.get('size', '')
                if size:
                    size_counts[size] = size_counts.get(size, 0) + 1
            preferred_size = max(size_counts, key=size_counts.get) if size_counts else 'N/A'

            # Determine tier
            if total_spent >= self.GOLD_THRESHOLD:
                tier = 'Gold'
                tier_emoji = '🥇'
            elif total_spent >= self.VIP_THRESHOLD:
                tier = 'VIP'
                tier_emoji = '⭐'
            else:
                tier = 'Regular'
                tier_emoji = '👤'

            # Loyalty points (1 point per 100 BDT spent)
            loyalty_points = int(total_spent / 100)

            # Last purchase
            last_order = orders[0]
            last_purchase_date = last_order.get('created_at', '')
            if hasattr(last_purchase_date, 'strftime'):
                days_since = (datetime.now() - last_purchase_date).days
            else:
                days_since = None

            # Activity status
            if days_since is not None:
                if days_since <= 30:
                    activity = 'Active'
                elif days_since <= 90:
                    activity = 'Moderate'
                else:
                    activity = 'Inactive'
            else:
                activity = 'Unknown'

            profile = {
                'found': True,
                'phone': phone,
                'name': orders[0].get('customer_name', 'Unknown'),
                'email': orders[0].get('customer_email', ''),
                'address': orders[0].get('address', ''),
                'district': orders[0].get('district', ''),
                'total_orders': total_orders,
                'total_spent': total_spent,
                'avg_order': avg_order,
                'tier': tier,
                'tier_emoji': tier_emoji,
                'loyalty_points': loyalty_points,
                'favorite_product': favorite,
                'preferred_size': preferred_size,
                'last_purchase': last_purchase_date,
                'days_since_purchase': days_since,
                'activity': activity,
                'orders': orders[:10],  # Last 10 orders
                '_cached_at': datetime.now()
            }

            self.cache[phone] = profile
            return profile

        except Exception as e:
            logger.error(f"CRM profile error: {e}")
            return {'error': str(e)}

    def get_top_customers(self, limit: int = 10) -> List[Dict]:
        """Get top customers by spending."""
        if not self.db:
            return []

        try:
            results = self.db.fetch_all(
                """SELECT customer_name, phone, 
                   COUNT(*) as order_count, 
                   SUM(COALESCE(NULLIF(total, 0), total_price, 0)) as total_spent,
                   MAX(created_at) as last_order
                   FROM orders 
                   GROUP BY customer_name, phone 
                   ORDER BY total_spent DESC 
                   LIMIT %s""",
                (limit,)
            )
            return results or []
        except Exception as e:
            logger.error(f"Top customers error: {e}")
            return []

    def get_returning_customers(self, min_orders: int = 2) -> List[Dict]:
        """Get customers with repeat purchases."""
        if not self.db:
            return []

        try:
            results = self.db.fetch_all(
                """SELECT customer_name, phone, 
                   COUNT(*) as order_count,
                   SUM(COALESCE(NULLIF(total, 0), total_price, 0)) as total_spent
                   FROM orders 
                   GROUP BY customer_name, phone 
                   HAVING COUNT(*) >= %s
                   ORDER BY order_count DESC""",
                (min_orders,)
            )
            return results or []
        except Exception as e:
            logger.error(f"Returning customers error: {e}")
            return []

    def get_inactive_customers(self, days: int = 60) -> List[Dict]:
        """Get customers who haven't ordered recently."""
        if not self.db:
            return []

        try:
            cutoff = datetime.now() - timedelta(days=days)
            results = self.db.fetch_all(
                """SELECT customer_name, phone,
                   MAX(created_at) as last_order,
                   COUNT(*) as total_orders,
                   SUM(COALESCE(NULLIF(total, 0), total_price, 0)) as total_spent
                   FROM orders 
                   GROUP BY customer_name, phone 
                   HAVING MAX(created_at) < %s
                   ORDER BY total_spent DESC
                   LIMIT 20""",
                (cutoff,)
            )
            return results or []
        except Exception as e:
            logger.error(f"Inactive customers error: {e}")
            return []

    def format_customer_profile(self, profile: Dict) -> str:
        """Format customer profile for Telegram."""
        if not profile.get('found'):
            return "❌ Customer not found."

        last_date = profile.get('last_purchase', '')
        if hasattr(last_date, 'strftime'):
            last_date = last_date.strftime('%b %d, %Y')

        # Recent orders
        orders_text = ""
        for o in profile.get('orders', [])[:5]:
            created = o.get('created_at', '')
            if hasattr(created, 'strftime'):
                created = created.strftime('%m/%d')
            total = o.get('total') or o.get('total_price') or 0
            orders_text += f"  • #{o.get('order_id', '?')} - {o.get('product_name', '?')} (৳{total}) [{created}]\n"

        return (
            f"{profile['tier_emoji']} *Customer Profile*\n"
            f"{'━' * 28}\n\n"
            f"👤 Name: *{profile['name']}*\n"
            f"📞 Phone: `{profile['phone']}`\n"
            f"📧 Email: {profile.get('email', 'N/A')}\n"
            f"📍 {profile.get('district', 'N/A')}\n\n"
            f"🏅 Tier: *{profile['tier']}*\n"
            f"🎯 Loyalty Points: *{profile['loyalty_points']}*\n\n"
            f"📊 *Purchase History:*\n"
            f"  Total Orders: {profile['total_orders']}\n"
            f"  Total Spent: ৳{profile['total_spent']:,.0f}\n"
            f"  Avg Order: ৳{profile['avg_order']:,.0f}\n"
            f"  Favorite: {profile['favorite_product']}\n"
            f"  Preferred Size: {profile['preferred_size']}\n\n"
            f"📅 Last Purchase: {last_date}\n"
            f"{'🟢' if profile['activity'] == 'Active' else '🟡' if profile['activity'] == 'Moderate' else '🔴'} Status: {profile['activity']}\n\n"
            f"📦 *Recent Orders:*\n{orders_text}"
        )

    def format_top_customers(self, customers: List[Dict]) -> str:
        """Format top customers list."""
        if not customers:
            return "No customer data available."

        text = f"👑 *Top Customers*\n{'━' * 28}\n\n"
        medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

        for i, c in enumerate(customers[:10]):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            text += (
                f"{medal} *{c.get('customer_name', '?')}*\n"
                f"    📞 {c.get('phone', '?')} | "
                f"📦 {c.get('order_count', 0)} orders | "
                f"💰 ৳{float(c.get('total_spent', 0)):,.0f}\n\n"
            )

        return text

    def get_status(self) -> str:
        cache_size = len(self.cache)
        return f"Active ({cache_size} cached profiles)" if self.db else "Inactive (no database)"


# Global instance
customer_crm = CustomerCRM()
