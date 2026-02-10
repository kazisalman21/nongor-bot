"""
Nongor Bot V3 - Courier Tracking Integration
Real-time delivery tracking via Pathao and Steadfast courier APIs.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests not installed - courier tracking disabled")


class CourierTracker:
    """Track deliveries across multiple Bangladeshi courier services."""

    # Courier status mappings to user-friendly text
    STATUS_MAP = {
        # Pathao statuses
        'Pickup Pending': {'emoji': '📋', 'text': 'Pickup Pending', 'stage': 1},
        'Picked Up': {'emoji': '📦', 'text': 'Picked Up by Courier', 'stage': 2},
        'In Transit': {'emoji': '🚚', 'text': 'In Transit', 'stage': 3},
        'At Hub': {'emoji': '🏢', 'text': 'At Distribution Hub', 'stage': 3},
        'Out for Delivery': {'emoji': '🛵', 'text': 'Out for Delivery', 'stage': 4},
        'Delivered': {'emoji': '✅', 'text': 'Delivered', 'stage': 5},
        'Returned': {'emoji': '↩️', 'text': 'Returned to Sender', 'stage': 0},
        'On Hold': {'emoji': '⏸️', 'text': 'On Hold', 'stage': 0},

        # Steadfast statuses
        'pending': {'emoji': '📋', 'text': 'Order Placed', 'stage': 1},
        'delivered_approval_pending': {'emoji': '📦', 'text': 'Delivery Approval Pending', 'stage': 4},
        'partial_delivered_approval_pending': {'emoji': '📦', 'text': 'Partial Delivery Pending', 'stage': 4},
        'cancelled_approval_pending': {'emoji': '❌', 'text': 'Cancellation Pending', 'stage': 0},
        'unknown_approval_pending': {'emoji': '❓', 'text': 'Under Review', 'stage': 0},
        'delivered': {'emoji': '✅', 'text': 'Delivered', 'stage': 5},
        'partial_delivered': {'emoji': '📦', 'text': 'Partially Delivered', 'stage': 5},
        'cancelled': {'emoji': '❌', 'text': 'Cancelled', 'stage': 0},
        'hold': {'emoji': '⏸️', 'text': 'On Hold', 'stage': 0},
        'in_review': {'emoji': '🔍', 'text': 'In Review', 'stage': 2},
    }

    def __init__(self):
        # Pathao Config
        self.pathao_base_url = os.getenv('PATHAO_API_URL', 'https://api-hermes.pathao.com')
        self.pathao_client_id = os.getenv('PATHAO_CLIENT_ID', '')
        self.pathao_client_secret = os.getenv('PATHAO_CLIENT_SECRET', '')
        self.pathao_username = os.getenv('PATHAO_USERNAME', '')
        self.pathao_password = os.getenv('PATHAO_PASSWORD', '')
        self.pathao_token = None

        # Steadfast Config
        self.steadfast_base_url = os.getenv('STEADFAST_API_URL', 'https://portal.steadfast.com.bd/api/v1')
        self.steadfast_api_key = os.getenv('STEADFAST_API_KEY', '')
        self.steadfast_secret_key = os.getenv('STEADFAST_SECRET_KEY', '')

        # Detect available couriers
        self.pathao_enabled = bool(self.pathao_client_id and self.pathao_client_secret)
        self.steadfast_enabled = bool(self.steadfast_api_key and self.steadfast_secret_key)

        if self.pathao_enabled:
            logger.info("Pathao courier tracking enabled")
        if self.steadfast_enabled:
            logger.info("Steadfast courier tracking enabled")
        if not self.pathao_enabled and not self.steadfast_enabled:
            logger.info("No courier APIs configured - tracking features limited")

    # ===========================
    # PATHAO
    # ===========================

    def _pathao_authenticate(self) -> bool:
        """Get Pathao API access token."""
        if not REQUESTS_AVAILABLE or not self.pathao_enabled:
            return False

        try:
            response = requests.post(
                f"{self.pathao_base_url}/aladdin/api/v1/issue-token",
                json={
                    'client_id': self.pathao_client_id,
                    'client_secret': self.pathao_client_secret,
                    'username': self.pathao_username,
                    'password': self.pathao_password,
                    'grant_type': 'password'
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.pathao_token = data.get('access_token')
                logger.info("Pathao authentication successful")
                return True
            else:
                logger.error(f"Pathao auth failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Pathao auth error: {e}")
            return False

    def track_pathao(self, consignment_id: str) -> Dict:
        """Track a Pathao shipment by consignment ID."""
        if not self.pathao_enabled or not REQUESTS_AVAILABLE:
            return {'success': False, 'error': 'Pathao tracking not configured'}

        # Ensure we have a token
        if not self.pathao_token:
            if not self._pathao_authenticate():
                return {'success': False, 'error': 'Pathao authentication failed'}

        try:
            response = requests.get(
                f"{self.pathao_base_url}/aladdin/api/v1/orders/{consignment_id}",
                headers={'Authorization': f'Bearer {self.pathao_token}'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json().get('data', {})
                status = data.get('order_status', 'Unknown')
                status_info = self.STATUS_MAP.get(status, {'emoji': '❓', 'text': status, 'stage': 0})

                return {
                    'success': True,
                    'courier': 'Pathao',
                    'tracking_id': consignment_id,
                    'status': status_info['text'],
                    'emoji': status_info['emoji'],
                    'stage': status_info['stage'],
                    'recipient': data.get('recipient_name', 'N/A'),
                    'address': data.get('recipient_address', 'N/A'),
                    'amount': data.get('amount_to_collect', 0),
                    'updated_at': data.get('updated_at', 'N/A'),
                    'raw': data
                }
            elif response.status_code == 401:
                # Token expired, retry once
                self.pathao_token = None
                if self._pathao_authenticate():
                    return self.track_pathao(consignment_id)
                return {'success': False, 'error': 'Authentication expired'}
            else:
                return {'success': False, 'error': f'Pathao API error ({response.status_code})'}

        except Exception as e:
            logger.error(f"Pathao tracking error: {e}")
            return {'success': False, 'error': str(e)}

    # ===========================
    # STEADFAST
    # ===========================

    def track_steadfast(self, invoice_id: str = None, tracking_code: str = None) -> Dict:
        """Track a Steadfast shipment by invoice ID or tracking code."""
        if not self.steadfast_enabled or not REQUESTS_AVAILABLE:
            return {'success': False, 'error': 'Steadfast tracking not configured'}

        try:
            headers = {
                'Api-Key': self.steadfast_api_key,
                'Secret-Key': self.steadfast_secret_key,
                'Content-Type': 'application/json'
            }

            if tracking_code:
                url = f"{self.steadfast_base_url}/status_by_trackingcode/{tracking_code}"
            elif invoice_id:
                url = f"{self.steadfast_base_url}/status_by_invoice/{invoice_id}"
            else:
                return {'success': False, 'error': 'Provide invoice_id or tracking_code'}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                status = data.get('delivery_status', 'unknown')
                status_info = self.STATUS_MAP.get(status, {'emoji': '❓', 'text': status, 'stage': 0})

                return {
                    'success': True,
                    'courier': 'Steadfast',
                    'tracking_id': tracking_code or invoice_id,
                    'status': status_info['text'],
                    'emoji': status_info['emoji'],
                    'stage': status_info['stage'],
                    'recipient': data.get('recipient_name', 'N/A'),
                    'address': data.get('recipient_address', 'N/A'),
                    'amount': data.get('cod_amount', 0),
                    'updated_at': data.get('updated_at', 'N/A'),
                    'raw': data
                }
            else:
                return {'success': False, 'error': f'Steadfast API error ({response.status_code})'}

        except Exception as e:
            logger.error(f"Steadfast tracking error: {e}")
            return {'success': False, 'error': str(e)}

    # ===========================
    # UNIFIED TRACKING
    # ===========================

    def track(self, tracking_id: str, courier: str = 'auto') -> Dict:
        """
        Universal tracking method.
        Auto-detects courier if not specified.
        """
        courier = courier.lower().strip()

        if courier == 'pathao' and self.pathao_enabled:
            return self.track_pathao(tracking_id)
        elif courier == 'steadfast' and self.steadfast_enabled:
            return self.track_steadfast(tracking_code=tracking_id)
        elif courier == 'auto':
            # Try all available couriers
            if self.steadfast_enabled:
                result = self.track_steadfast(tracking_code=tracking_id)
                if result['success']:
                    return result

            if self.pathao_enabled:
                result = self.track_pathao(tracking_id)
                if result['success']:
                    return result

            return {'success': False, 'error': 'Could not find shipment with any courier'}
        else:
            return {'success': False, 'error': f'Unknown courier: {courier}'}

    def format_tracking_message(self, result: Dict) -> str:
        """Format tracking result as a beautiful Telegram message."""
        if not result.get('success'):
            return (
                "❌ *Tracking Failed*\n\n"
                f"Error: {result.get('error', 'Unknown error')}\n\n"
                "Please verify your tracking ID and try again."
            )

        # Progress bar
        stage = result.get('stage', 0)
        stages = ['📋', '📦', '🚚', '🛵', '✅']
        progress = ''
        for i, s in enumerate(stages):
            if i < stage:
                progress += f'{s}━'
            elif i == stage:
                progress += f'{s}'
            else:
                progress += f'╌{s}'

        return (
            f"📦 *Courier Tracking*\n"
            f"{'━' * 25}\n\n"
            f"🏢 Courier: *{result.get('courier', 'N/A')}*\n"
            f"🔖 Tracking: `{result.get('tracking_id', 'N/A')}`\n\n"
            f"{result.get('emoji', '❓')} Status: *{result.get('status', 'Unknown')}*\n\n"
            f"Progress:\n{progress}\n\n"
            f"👤 Recipient: {result.get('recipient', 'N/A')}\n"
            f"📍 Address: {result.get('address', 'N/A')}\n"
            f"💰 COD: ৳{result.get('amount', 0)}\n"
            f"🕐 Updated: {result.get('updated_at', 'N/A')}"
        )

    def get_available_couriers(self) -> List[str]:
        """Return list of configured courier names."""
        couriers = []
        if self.pathao_enabled:
            couriers.append('Pathao')
        if self.steadfast_enabled:
            couriers.append('Steadfast')
        return couriers

    def get_status(self) -> str:
        """Return courier tracking status string."""
        couriers = self.get_available_couriers()
        if couriers:
            return f"Active ({', '.join(couriers)})"
        return "Disabled (no courier APIs configured)"


# Global instance
courier_tracker = CourierTracker()
