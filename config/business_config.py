"""
Nongor Bot V3 - Business Configuration
Static business policies and information for AI context
"""

# ===============================================
# DELIVERY POLICIES
# ===============================================
DELIVERY_POLICIES = {
    "dhaka": {
        "name": "Inside Dhaka",
        "charge": 60,
        "time": "1-2 business days",
        "free_above": 1000
    },
    "outside_dhaka": {
        "name": "Outside Dhaka", 
        "charge": 120,
        "time": "3-5 business days",
        "free_above": 2000
    }
}

# ===============================================
# PAYMENT METHODS
# ===============================================
PAYMENT_METHODS = {
    "cod": {
        "name": "Cash on Delivery",
        "description": "Pay when you receive your order",
        "available": True
    },
    "bkash": {
        "name": "bKash",
        "number": "+880 1711-222333",
        "available": True
    },
    "nagad": {
        "name": "Nagad",
        "number": "+880 1711-222333",
        "available": True
    },
    "rocket": {
        "name": "Rocket",
        "number": "+880 1711-222333",
        "available": True
    }
}

# ===============================================
# RETURN & EXCHANGE POLICIES
# ===============================================
RETURN_POLICIES = {
    "exchange_window": 7,  # days
    "conditions": [
        "Product tags must be intact",
        "Product must be unworn and unwashed",
        "Original packaging required"
    ],
    "size_exchange": {
        "allowed": True,
        "free": True,
        "description": "Free size exchange - we cover shipping both ways"
    },
    "sale_items": {
        "refund": False,
        "exchange": True,
        "description": "Sale items: Exchange only, no refunds"
    },
    "defective_items": {
        "refund": True,
        "window": 3,  # days
        "description": "Full refund for defective items within 3 days"
    }
}

# ===============================================
# CONTACT INFORMATION
# ===============================================
CONTACT_INFO = {
    "phone": "+880 1711-222333",
    "whatsapp": "+880 1711-222333",
    "email": "support@nongor.com",
    "facebook": "https://facebook.com/nongor",
    "website": "https://nongor-brand.vercel.app"
}

# ===============================================
# BUSINESS HOURS
# ===============================================
BUSINESS_HOURS = {
    "weekdays": {
        "days": "Saturday - Thursday",
        "hours": "10:00 AM - 8:00 PM"
    },
    "friday": {
        "days": "Friday",
        "hours": "Closed (Weekly Holiday)"
    },
    "response_times": {
        "whatsapp": "5-10 minutes",
        "email": "24 hours",
        "facebook": "1-2 hours"
    }
}

# ===============================================
# SIZE GUIDE
# ===============================================
SIZE_GUIDE = {
    "S": {
        "chest": "36-38 inches",
        "length": "26 inches",
        "height": "5'4\" - 5'6\"",
        "weight": "55-65 kg"
    },
    "M": {
        "chest": "38-40 inches",
        "length": "27 inches", 
        "height": "5'6\" - 5'8\"",
        "weight": "65-75 kg"
    },
    "L": {
        "chest": "40-42 inches",
        "length": "28 inches",
        "height": "5'8\" - 5'10\"",
        "weight": "75-85 kg"
    },
    "XL": {
        "chest": "42-44 inches",
        "length": "29 inches",
        "height": "5'10\" - 6'0\"",
        "weight": "85-95 kg"
    },
    "XXL": {
        "chest": "44-46 inches",
        "length": "30 inches",
        "height": "6'0\"+",
        "weight": "95+ kg"
    }
}

# ===============================================
# ORDER STATUS DEFINITIONS
# ===============================================
ORDER_STATUSES = {
    "pending": {
        "emoji": "⏳",
        "label": "Pending",
        "description": "Order received, awaiting confirmation"
    },
    "confirmed": {
        "emoji": "✅",
        "label": "Confirmed",
        "description": "Order confirmed, preparing for shipment"
    },
    "processing": {
        "emoji": "📦",
        "label": "Processing",
        "description": "Order is being packed"
    },
    "shipped": {
        "emoji": "🚚",
        "label": "Shipped",
        "description": "Order has been dispatched"
    },
    "delivered": {
        "emoji": "✅",
        "label": "Delivered",
        "description": "Order successfully delivered"
    },
    "cancelled": {
        "emoji": "❌",
        "label": "Cancelled",
        "description": "Order was cancelled"
    }
}

# ===============================================
# AI BEHAVIOR GUIDELINES
# ===============================================
AI_GUIDELINES = """
CUSTOMER SERVICE GUIDELINES FOR AI:

PERSONALITY:
- Be friendly, warm, and professional
- Use appropriate Bengali cultural references
- Add emojis to make responses feel friendly
- Keep responses concise but informative

ACCURACY:
- Always use real product data from database
- Never make up product names or prices
- If unsure, offer to connect with human support
- Be honest about stock availability

HELPFULNESS:
- Proactively offer related information
- Suggest alternatives if item is out of stock
- Help with sizing recommendations
- Guide customers through the ordering process

ESCALATION:
- Offer human support for complex issues
- Provide contact information when needed
- Never argue with customers
- Apologize for any inconvenience

LANGUAGE:
- Use simple, clear English
- Understand common Bengali transliterations
- Handle both English and Bangla queries
"""

# ===============================================
# HELPER FUNCTIONS
# ===============================================

def get_full_policy_text() -> str:
    """Generate complete policy text for AI context"""
    
    text = """
BUSINESS POLICIES & INFORMATION:

DELIVERY:
"""
    for key, policy in DELIVERY_POLICIES.items():
        text += f"- {policy['name']}: {policy['time']} (৳{policy['charge']} charge)\n"
        text += f"  Free delivery on orders above ৳{policy['free_above']}\n"
    
    text += "\nPAYMENT METHODS:\n"
    for key, method in PAYMENT_METHODS.items():
        if method['available']:
            text += f"- {method['name']}"
            if 'number' in method:
                text += f": {method['number']}"
            text += "\n"
    
    text += "\nRETURN & EXCHANGE:\n"
    text += f"- Exchange within {RETURN_POLICIES['exchange_window']} days\n"
    for condition in RETURN_POLICIES['conditions']:
        text += f"  • {condition}\n"
    text += f"- {RETURN_POLICIES['size_exchange']['description']}\n"
    text += f"- {RETURN_POLICIES['sale_items']['description']}\n"
    text += f"- {RETURN_POLICIES['defective_items']['description']}\n"
    
    text += "\nCONTACT:\n"
    text += f"- Phone/WhatsApp: {CONTACT_INFO['phone']}\n"
    text += f"- Email: {CONTACT_INFO['email']}\n"
    text += f"- Facebook: {CONTACT_INFO['facebook']}\n"
    text += f"- Website: {CONTACT_INFO['website']}\n"
    
    text += "\nBUSINESS HOURS:\n"
    text += f"- {BUSINESS_HOURS['weekdays']['days']}: {BUSINESS_HOURS['weekdays']['hours']}\n"
    text += f"- {BUSINESS_HOURS['friday']['days']}: {BUSINESS_HOURS['friday']['hours']}\n"
    
    text += "\n" + AI_GUIDELINES
    
    return text


def get_size_recommendation(height_cm: int, weight_kg: int) -> str:
    """Recommend size based on height and weight"""
    
    if weight_kg < 65 and height_cm < 170:
        return "S"
    elif weight_kg < 75 and height_cm < 175:
        return "M"
    elif weight_kg < 85 and height_cm < 180:
        return "L"
    elif weight_kg < 95 and height_cm < 185:
        return "XL"
    else:
        return "XXL"


def get_status_info(status: str) -> dict:
    """Get status emoji and description"""
    return ORDER_STATUSES.get(status.lower(), ORDER_STATUSES['pending'])
