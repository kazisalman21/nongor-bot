"""
Nongor Bot V3 - Package Initializer
"""

from .database_enhanced import Database, get_database
from .ai_context_builder import (
    get_full_ai_context,
    get_database_context,
    get_order_details,
    format_order_details,
    clear_context_cache
)
from .config.business_config import (
    DELIVERY_POLICIES,
    PAYMENT_METHODS,
    RETURN_POLICIES,
    CONTACT_INFO,
    BUSINESS_HOURS,
    SIZE_GUIDE,
    ORDER_STATUSES
)

__version__ = "3.0.0"
__author__ = "Nongor Team"
