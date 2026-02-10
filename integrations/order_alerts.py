"""
Nongor Bot V3 - Real-time Order Alert System
Polls database for new orders and notifies admins instantly.
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class OrderAlertSystem:
    """Real-time order notifications for admins via Telegram."""

    def __init__(self):
        self.poll_interval = int(os.getenv('ORDER_POLL_INTERVAL', '60'))
        self.enabled = False
        self.running = False
        self.task = None
        self.last_seen_order_id = None
        self.total_alerts_sent = 0
        self.db = None

    def set_database(self, db):
        """Set database instance for order queries."""
        self.db = db

    async def start(self, admin_ids: List[int], bot, db=None) -> bool:
        """Start order polling in background."""
        if self.running:
            return False

        if db:
            self.db = db

        if not self.db:
            logger.warning("Order alerts: no database configured")
            return False

        self.enabled = True
        self.running = True
        self.task = asyncio.create_task(
            self._poll_loop(admin_ids, bot)
        )
        logger.info(f"Order alert system started (interval: {self.poll_interval}s)")
        return True

    async def stop(self) -> bool:
        """Stop order polling."""
        self.enabled = False
        self.running = False
        if self.task:
            self.task.cancel()
            self.task = None
        logger.info("Order alert system stopped")
        return True

    async def _poll_loop(self, admin_ids: List[int], bot):
        """Main polling loop."""
        try:
            # Initial delay
            await asyncio.sleep(10)

            # Initialize: get latest order ID
            if self.last_seen_order_id is None:
                try:
                    result = self.db.fetch_one(
                        "SELECT order_id FROM orders ORDER BY created_at DESC LIMIT 1"
                    )
                    if result:
                        self.last_seen_order_id = result.get('order_id')
                        logger.info(f"Order tracking initialized at ID: {self.last_seen_order_id}")
                except Exception as e:
                    logger.error(f"Failed to init order tracking: {e}")

            while self.enabled:
                try:
                    if self.last_seen_order_id is not None:
                        # Check for new orders
                        new_orders = self.db.fetch_all(
                            "SELECT * FROM orders WHERE order_id > %s ORDER BY created_at ASC",
                            (self.last_seen_order_id,)
                        )

                        for order in (new_orders or []):
                            self.last_seen_order_id = order.get('order_id')
                            self.total_alerts_sent += 1

                            msg = self._format_new_order_alert(order)
                            await self._alert_admins(admin_ids, bot, msg)
                    else:
                        # Still couldn't get last order, try again
                        result = self.db.fetch_one(
                            "SELECT order_id FROM orders ORDER BY created_at DESC LIMIT 1"
                        )
                        if result:
                            self.last_seen_order_id = result.get('order_id')

                except Exception as e:
                    logger.error(f"Order polling error: {e}")

                await asyncio.sleep(self.poll_interval)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Order alert loop error: {e}")
        finally:
            self.running = False

    def _format_new_order_alert(self, order: Dict) -> str:
        """Format a new order notification message."""
        order_id = order.get('order_id', 'N/A')
        customer = order.get('customer_name', 'Unknown')
        phone = order.get('phone', 'N/A')
        product = order.get('product_name', 'N/A')
        size = order.get('size', '')
        qty = order.get('quantity', 1)
        total = order.get('total') or order.get('total_price') or 0

        address = order.get('address', 'N/A')
        district = order.get('district', '')

        created = order.get('created_at', datetime.now())
        if hasattr(created, 'strftime'):
            created = created.strftime('%Y-%m-%d %H:%M')

        return (
            f"🎉 *NEW ORDER!*\n"
            f"{'━' * 25}\n\n"
            f"🆔 Order: `#{order_id}`\n"
            f"👤 Customer: {customer}\n"
            f"📞 Phone: {phone}\n\n"
            f"🛍️ Product: {product}\n"
            f"📏 Size: {size} | Qty: {qty}\n"
            f"💰 Total: *৳{total}*\n\n"
            f"📍 {address}"
            f"{f', {district}' if district else ''}\n"
            f"🕐 {created}"
        )

    async def _alert_admins(self, admin_ids: List[int], bot, message: str):
        """Send alert to all admins."""
        for uid in admin_ids:
            try:
                await bot.send_message(
                    chat_id=uid, text=message, parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {uid}: {e}")

    def get_status(self) -> str:
        """Return alert system status."""
        if self.running:
            return f"Active (polling every {self.poll_interval}s, {self.total_alerts_sent} alerts sent)"
        return "Inactive"


# Global instance
order_alerts = OrderAlertSystem()
