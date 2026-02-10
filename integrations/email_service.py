"""
Nongor Bot V3 - Email Service (SendGrid Integration)
Handles order confirmations, shipping notifications, and inventory alerts.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Try importing SendGrid
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import (
        Mail, Email, To, Content, HtmlContent,
        Subject, Attachment, FileContent, FileName,
        FileType, Disposition
    )
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logger.warning("SendGrid not installed - email features disabled. Install with: pip install sendgrid")


class EmailService:
    """Premium email service using SendGrid for transactional emails."""

    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY', '')
        self.from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@nongor.com')
        self.from_name = os.getenv('SENDGRID_FROM_NAME', 'Nongor Premium')
        self.enabled = bool(self.api_key) and SENDGRID_AVAILABLE
        self.client = None

        if self.enabled:
            self.client = SendGridAPIClient(self.api_key)
            logger.info("Email service initialized (SendGrid)")
        else:
            if not SENDGRID_AVAILABLE:
                logger.info("Email service disabled - sendgrid package not installed")
            else:
                logger.info("Email service disabled - SENDGRID_API_KEY not set")

    def _send_email(self, to_email: str, subject: str, html_content: str) -> Dict:
        """Send an email via SendGrid."""
        if not self.enabled:
            return {'success': False, 'error': 'Email service not configured'}

        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=Subject(subject),
                html_content=HtmlContent(html_content)
            )

            response = self.client.send(message)

            result = {
                'success': response.status_code in [200, 201, 202],
                'status_code': response.status_code,
                'message_id': response.headers.get('X-Message-Id', 'N/A')
            }

            if result['success']:
                logger.info(f"Email sent to {to_email}: {subject}")
            else:
                logger.error(f"Email failed ({response.status_code}): {to_email}")

            return result

        except Exception as e:
            logger.error(f"Email send error: {e}")
            return {'success': False, 'error': str(e)}

    def send_order_confirmation(self, order_data: Dict) -> Dict:
        """Send order confirmation email to customer."""
        customer_email = order_data.get('customer_email', '')
        if not customer_email:
            return {'success': False, 'error': 'No customer email provided'}

        order_id = order_data.get('order_id', 'N/A')
        customer_name = order_data.get('customer_name', 'Valued Customer')
        product = order_data.get('product_name', 'N/A')
        size = order_data.get('size', '')
        qty = order_data.get('quantity', 1)
        total = order_data.get('total') or order_data.get('total_price') or 0
        items = order_data.get('items', []) # Note: items list might be empty
        phone = order_data.get('phone', 'N/A')
        address = order_data.get('address', 'N/A')
        district = order_data.get('district', 'N/A')

        # Build items HTML
        items_html = ""
        if items:
            for item in items:
                items_html += f"""
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 12px;">{item.get('name', 'Product')}</td>
                    <td style="padding: 12px; text-align: center;">{item.get('size', '-')}</td>
                    <td style="padding: 12px; text-align: center;">{item.get('quantity', 1)}</td>
                    <td style="padding: 12px; text-align: right;">৳{item.get('price', 0)}</td>
                </tr>
                """
        else:
            # Fallback to order-level item details
            items_html = f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 12px;">{product}</td>
                <td style="padding: 12px; text-align: center;">{size if size else '-'}</td>
                <td style="padding: 12px; text-align: center;">{qty}</td>
                <td style="padding: 12px; text-align: right;">৳{total}</td>
            </tr>
            """

        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="color: #e94560; margin: 0; font-size: 28px;">NONGOR</h1>
                <p style="color: #ccc; margin: 5px 0 0;">Premium Fashion</p>
            </div>

            <!-- Content -->
            <div style="padding: 30px; background: #f8f9fa; border: 1px solid #eee;">
                <h2 style="color: #1a1a2e; margin-top: 0;">Order Confirmed! ✓</h2>
                <p style="color: #555;">Dear <strong>{customer_name}</strong>,</p>
                <p style="color: #555;">Thank you for your order! Here are the details:</p>

                <!-- Order Info -->
                <div style="background: #fff; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #e94560;">
                    <p style="margin: 5px 0;"><strong>Order ID:</strong> #{order_id}</p>
                    <p style="margin: 5px 0;"><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                    <p style="margin: 5px 0;"><strong>Phone:</strong> {phone}</p>
                    <p style="margin: 5px 0;"><strong>Address:</strong> {address}</p>
                </div>

                <!-- Items Table -->
                <table style="width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden;">
                    <thead>
                        <tr style="background: #1a1a2e; color: #fff;">
                            <th style="padding: 12px; text-align: left;">Product</th>
                            <th style="padding: 12px; text-align: center;">Size</th>
                            <th style="padding: 12px; text-align: center;">Qty</th>
                            <th style="padding: 12px; text-align: right;">Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                    <tfoot>
                        <tr style="background: #f0f0f0;">
                            <td colspan="3" style="padding: 12px; text-align: right;"><strong>Total:</strong></td>
                            <td style="padding: 12px; text-align: right; color: #e94560; font-size: 18px;"><strong>৳{total}</strong></td>
                        </tr>
                    </tfoot>
                </table>

                <!-- Tracking -->
                <div style="background: #e8f5e9; border-radius: 8px; padding: 15px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0; color: #2e7d32;">Track your order anytime on our Telegram Bot!</p>
                    <p style="margin: 5px 0 0; font-size: 12px; color: #666;">Use your phone number or Order ID #{order_id}</p>
                </div>
            </div>

            <!-- Footer -->
            <div style="background: #1a1a2e; padding: 20px; text-align: center; border-radius: 0 0 8px 8px;">
                <p style="color: #888; font-size: 12px; margin: 0;">Nongor Premium Fashion | Dhaka, Bangladesh</p>
                <p style="color: #666; font-size: 11px; margin: 5px 0 0;">You received this email because you placed an order.</p>
            </div>
        </div>
        """

        return self._send_email(
            to_email=customer_email,
            subject=f"Order Confirmed - #{order_id} | Nongor",
            html_content=html
        )

    def send_shipping_notification(self, order_data: Dict, tracking_info: Dict) -> Dict:
        """Send shipping notification with courier tracking details."""
        customer_email = order_data.get('customer_email', '')
        if not customer_email:
            return {'success': False, 'error': 'No customer email provided'}

        order_id = order_data.get('order_id', 'N/A')
        customer_name = order_data.get('customer_name', 'Valued Customer')
        courier = tracking_info.get('courier', 'N/A')
        tracking_id = tracking_info.get('tracking_id', 'N/A')
        estimated_delivery = tracking_info.get('estimated_delivery', '3-5 business days')

        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="color: #e94560; margin: 0;">NONGOR</h1>
                <p style="color: #ccc; margin: 5px 0 0;">Your Order is On Its Way!</p>
            </div>

            <div style="padding: 30px; background: #f8f9fa; border: 1px solid #eee;">
                <h2 style="color: #1a1a2e; margin-top: 0;">📦 Shipped!</h2>
                <p>Dear <strong>{customer_name}</strong>,</p>
                <p>Great news! Your order <strong>#{order_id}</strong> has been shipped.</p>

                <div style="background: #fff; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #4caf50;">
                    <p style="margin: 5px 0;"><strong>Courier:</strong> {courier}</p>
                    <p style="margin: 5px 0;"><strong>Tracking ID:</strong> <code>{tracking_id}</code></p>
                    <p style="margin: 5px 0;"><strong>Est. Delivery:</strong> {estimated_delivery}</p>
                </div>

                <div style="text-align: center; margin: 20px 0;">
                    <p style="color: #555;">Track your parcel on our Telegram bot or contact us for updates!</p>
                </div>
            </div>

            <div style="background: #1a1a2e; padding: 20px; text-align: center; border-radius: 0 0 8px 8px;">
                <p style="color: #888; font-size: 12px; margin: 0;">Nongor Premium Fashion</p>
            </div>
        </div>
        """

        return self._send_email(
            to_email=customer_email,
            subject=f"Your Order #{order_id} Has Been Shipped! | Nongor",
            html_content=html
        )

    def send_inventory_alert(self, items: List[Dict], admin_email: str) -> Dict:
        """Send low stock alert to admin."""
        if not items:
            return {'success': False, 'error': 'No items to report'}

        rows = ""
        for item in items:
            stock = item.get('stock', 0)
            color = '#e94560' if stock <= 2 else '#ff9800'
            rows += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{item.get('name', 'Unknown')}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{item.get('size', '-')}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; color: {color}; font-weight: bold; text-align: center;">{stock}</td>
            </tr>
            """

        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #e94560; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                <h2 style="color: #fff; margin: 0;">⚠️ Low Stock Alert</h2>
            </div>

            <div style="padding: 20px; background: #fff; border: 1px solid #eee;">
                <p>{len(items)} product(s) are running low on stock:</p>

                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f5f5f5;">
                            <th style="padding: 10px; text-align: left;">Product</th>
                            <th style="padding: 10px; text-align: left;">Size</th>
                            <th style="padding: 10px; text-align: center;">Stock</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>

                <p style="margin-top: 20px; color: #666; font-size: 13px;">
                    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        </div>
        """

        return self._send_email(
            to_email=admin_email,
            subject=f"[ALERT] {len(items)} Products Low on Stock | Nongor",
            html_content=html
        )

    def get_status(self) -> str:
        """Return email service status string."""
        if not SENDGRID_AVAILABLE:
            return "Disabled (sendgrid not installed)"
        if not self.api_key:
            return "Disabled (no API key)"
        return f"Active (from: {self.from_email})"


# Global instance
email_service = EmailService()
