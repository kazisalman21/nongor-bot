"""
Nongor Bot V3 - AI Context Builder
Aggregates context from database, website, and business policies for AI
"""

import os
import re
import time
import logging
import asyncio
from typing import Optional, Dict
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from database_enhanced import get_database
from config.business_config import get_full_policy_text

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# ===============================================
# CACHING SYSTEM
# ===============================================

class ContextCache:
    """Simple in-memory cache for AI context"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict] = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[str]:
        """Get cached value if not expired"""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['value']
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: str):
        """Set cache value with timestamp"""
        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()


# Global cache instance
_cache = ContextCache(ttl_seconds=int(os.getenv('CONTEXT_CACHE_SECONDS', 300)))


# ===============================================
# DATABASE CONTEXT
# ===============================================

async def get_database_context() -> str:
    """
    Fetch real-time data from database:
    1. All available products (name, stock, price)
    2. Today's sales stats (orders, revenue)
    3. Popular products (last 30 days)
    4. Low stock items
    
    Returns formatted context for AI
    """
    
    # Check cache first
    cached = _cache.get('database_context')
    if cached:
        return cached
    
    try:
        db = get_database()
        
        # Get products
        products_text = db.get_products_for_context()
        
        # Get stats
        stats_text = db.get_stats_for_context()
        
        # Get top products
        top_products = db.get_top_products(days=30, limit=5)
        top_text = "\nPOPULAR PRODUCTS (Last 30 days):\n"
        for i, p in enumerate(top_products, 1):
            top_text += f"{i}. {p['product_name']}: {p['order_count']} orders, ৳{p['revenue']:,.0f}\n"
        
        # Get low stock alerts
        low_stock = db.get_low_stock_items(threshold=10)
        low_stock_text = "\nLOW STOCK ALERTS:\n" if low_stock else ""
        for item in low_stock[:5]:
            low_stock_text += f"⚠️ {item['name']}: Only {item['stock_quantity']} left\n"
        
        # Combine context
        context = f"""
DATABASE INFO (Live Data):

{products_text}

{stats_text}
{top_text}
{low_stock_text}
"""
        
        # Cache result
        _cache.set('database_context', context)
        
        return context
        
    except Exception as e:
        logger.error(f"Error fetching database context: {e}")
        return """
DATABASE INFO:
⚠️ Unable to fetch live data. Using cached information.
Please check database connection.
"""


# ===============================================
# WEBSITE SCRAPING
# ===============================================

async def scrape_website_info() -> str:
    """
    Scrape website for:
    1. Meta description
    2. Page title
    3. Main headings (product categories)
    4. Any announcements/banners
    
    Uses requests + BeautifulSoup
    """
    
    # Check if scraping is enabled
    if not os.getenv('ENABLE_WEB_SCRAPING', 'true').lower() == 'true':
        return "WEBSITE INFO: Web scraping disabled."
    
    # Check cache
    cached = _cache.get('website_context')
    if cached:
        return cached
    
    website_url = os.getenv('WEBSITE_URL', 'https://nongor-brand.vercel.app')
    
    try:
        # Make request with timeout
        response = requests.get(website_url, timeout=10, headers={
            'User-Agent': 'NongorBot/3.0 (Context Builder)'
        })
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract metadata
        title = soup.title.string if soup.title else "Nongor Premium"
        
        meta_desc = ""
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_tag and meta_tag.get('content'):
            meta_desc = meta_tag['content']
        
        # Extract categories (look for common patterns)
        categories = []
        for heading in soup.find_all(['h2', 'h3'], limit=10):
            text = heading.get_text(strip=True)
            if text and len(text) < 50:
                categories.append(text)
        
        # Look for sale/promotion banners
        promotions = []
        for element in soup.find_all(class_=re.compile(r'(banner|promo|sale|offer)', re.I)):
            text = element.get_text(strip=True)
            if text and len(text) < 100:
                promotions.append(text[:100])
        
        # Build context
        context = f"""
WEBSITE INFO:
Title: {title}
Description: {meta_desc[:200] if meta_desc else 'Quality clothing for modern Bangladesh'}
URL: {website_url}
"""
        
        if categories:
            context += f"Sections: {', '.join(categories[:5])}\n"
        
        if promotions:
            context += f"Current Promotions: {promotions[0]}\n"
        
        # Cache result
        _cache.set('website_context', context)
        
        return context
        
    except requests.Timeout:
        logger.warning("Website scraping timeout")
        return f"""
WEBSITE INFO:
URL: {website_url}
Status: Website available but slow to respond
"""
    except Exception as e:
        logger.error(f"Website scraping error: {e}")
        return f"""
WEBSITE INFO:
URL: {website_url}
Description: Nongor Premium - Quality clothing for modern Bangladesh
Categories: T-Shirts, Hoodies, Jackets, Accessories
"""


# ===============================================
# BUSINESS POLICIES
# ===============================================

def get_business_policies() -> str:
    """
    Return comprehensive business information:
    - Delivery policies
    - Payment methods
    - Return/exchange policies
    - Contact information
    - Business hours
    - Customer service guidelines
    """
    return get_full_policy_text()


# ===============================================
# FULL CONTEXT ASSEMBLY
# ===============================================

async def get_full_ai_context(user_role: str = "user") -> str:
    """
    Combine all context sources for complete AI context.
    
    Args:
        user_role: 'admin' or 'user' - determines context depth
        
    Returns:
        Complete context string for AI system prompt
    """
    
    cache_key = f'full_context_{user_role}'
    cached = _cache.get(cache_key)
    if cached:
        return cached
    
    # Base context
    base_context = """
You are a helpful customer service AI assistant for Nongor Premium,
a premium clothing e-commerce brand in Bangladesh.

Your goal is to help customers with:
- Product information and recommendations
- Size guidance based on their measurements
- Order tracking and status
- Business policies (delivery, returns, payments)
- General inquiries

"""
    
    # Gather context from all sources
    try:
        database_context = await get_database_context()
    except:
        database_context = "DATABASE: Unable to fetch live data."
    
    try:
        website_context = await scrape_website_info()
    except:
        website_context = "WEBSITE: Information unavailable."
    
    business_policies = get_business_policies()
    
    # Build full context based on role
    if user_role == "admin":
        full_context = f"""
{base_context}

You are in ADMIN MODE. You have access to business analytics and can provide
insights about sales, inventory, and customer behavior.

{database_context}

{website_context}

{business_policies}

ADMIN CAPABILITIES:
- Provide sales analysis and insights
- Suggest inventory restocking priorities
- Analyze customer trends
- Generate business reports
- Offer marketing suggestions based on data

INSTRUCTIONS:
- Use actual data from the database above
- Provide specific numbers when available
- Offer actionable business insights
- Help with strategic decisions
- Be analytical and data-driven
"""
    else:
        # User mode - simpler context
        full_context = f"""
{base_context}

{database_context}

{website_context}

{business_policies}

USER MODE INSTRUCTIONS:
- Be friendly, warm, and helpful
- Use appropriate emojis to seem approachable
- Provide accurate product information from database
- Help users track orders by phone or order ID
- Give sizing recommendations when asked
- Explain policies clearly
- If unsure, offer to connect with human support
- Keep responses concise but informative
- Never make up information - be honest if unavailable
"""
    
    # Cache the full context
    _cache.set(cache_key, full_context)
    
    return full_context


# ===============================================
# ORDER TRACKING HELPERS
# ===============================================

async def get_order_details(order_id: int = None, phone: str = None) -> Optional[Dict]:
    """
    Fetch order details by ID or phone number.
    
    Args:
        order_id: Order ID to look up
        phone: Phone number to look up
        
    Returns:
        Order dict or None if not found
    """
    db = get_database()
    
    if order_id:
        return db.get_order_by_id(order_id)
    elif phone:
        return db.get_order_by_phone(phone)
    
    return None


async def format_order_details(order: Dict) -> str:
    """
    Format order dict into readable text.
    
    Args:
        order: Order dictionary from database
        
    Returns:
        Formatted order text
    """
    from config.business_config import get_status_info
    
    if not order:
        return "❌ Order not found. Please check the order ID or phone number."
    
    status_info = get_status_info(order.get('status', 'pending'))
    
    # Format payment status
    payment_status = order.get('payment_status', 'pending')
    payment_emoji = "✅" if payment_status == 'paid' else "⏳"
    
    text = f"""
📦 **ORDER DETAILS**
═══════════════════════════════
🆔 **Order ID:** #{order.get('order_id', order.get('id', 'N/A'))}
👤 **Customer:** {order.get('customer_name', 'N/A')}
📱 **Phone:** {order.get('customer_phone', 'N/A')}

💰 **PAYMENT:**
• Total: ৳{order.get('total', 0):,.2f}
• Payment: {payment_emoji} {payment_status.upper()}
• Method: {order.get('payment_method', 'N/A').upper()}

📊 **ORDER STATUS:**
{status_info['emoji']} **{status_info['label']}**
_{status_info['description']}_

📅 Ordered: {format_datetime(order.get('created_at'))}
═══════════════════════════════
"""
    
    # Add next step hints
    status = order.get('status', '').lower()
    if status == 'pending':
        text += "\n📌 **Next:** Order is being reviewed. You'll receive confirmation soon!"
    elif status == 'processing':
        text += "\n📌 **Next:** Your order is being packed and will ship soon!"
    elif status == 'shipped':
        text += "\n📌 **Next:** Order is on the way! Expected delivery in 1-3 days."
    elif status == 'delivered':
        text += "\n✅ Order delivered! Thank you for shopping with Nongor! 💚"
    
    text += "\n\n❓ Questions? Contact: +880 1711-222333"
    
    return text


def format_datetime(dt) -> str:
    """Format datetime to readable string"""
    if not dt:
        return "N/A"
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt
    
    return dt.strftime("%d %b %Y, %I:%M %p")


# ===============================================
# PRODUCT SEARCH HELPERS
# ===============================================

async def search_products_for_ai(query: str) -> str:
    """
    Search products and format for AI response.
    
    Args:
        query: Search term
        
    Returns:
        Formatted product list
    """
    db = get_database()
    products = db.search_products(query)
    
    if not products:
        return f"No products found matching '{query}'. Try a different search term or browse all products."
    
    text = f"📦 **Products matching '{query}':**\n\n"
    
    for p in products[:5]:
        stock_status = "✅ In Stock" if p['stock_quantity'] > 10 else f"⚠️ Only {p['stock_quantity']} left"
        text += f"• **{p['name']}**\n"
        text += f"  💰 ৳{p['price']:,.0f} | {stock_status}\n\n"
    
    return text


# ===============================================
# CACHE MANAGEMENT
# ===============================================

def clear_context_cache():
    """Clear all cached context (call when data changes)"""
    _cache.clear()
    logger.info("Context cache cleared")


def get_cache_stats() -> Dict:
    """Get cache statistics"""
    return {
        'entries': len(_cache.cache),
        'ttl_seconds': _cache.ttl
    }
