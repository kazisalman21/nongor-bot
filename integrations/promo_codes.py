import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PromoCodeEngine:
    """In-memory promo code management (persistent via admin commands)."""

    def __init__(self):
        self.codes: Dict[str, Dict] = {}
        self.redemptions: List[Dict] = []
        self.promos_file = os.getenv('PROMO_DATA_FILE', 'promos.json')

        # Pre-load some default codes
        self._init_defaults()
        # Load from disk if exists
        self.load()

    def _init_defaults(self):
        """Initialize with sample promo codes."""
        self.codes = {
            'WELCOME10': {
                'code': 'WELCOME10',
                'type': 'percentage',
                'value': 10,
                'max_uses': 100,
                'used': 0,
                'min_order': 500,
                'expires': datetime(2026, 12, 31),
                'active': True,
                'description': 'Welcome discount - 10% off'
            },
            'NONGOR50': {
                'code': 'NONGOR50',
                'type': 'fixed',
                'value': 50,
                'max_uses': 50,
                'used': 0,
                'min_order': 300,
                'expires': datetime(2026, 6, 30),
                'active': True,
                'description': '৳50 off on orders above ৳300'
            }
        }

    def create_code(self, code: str, discount_type: str, value: float,
                    max_uses: int = 100, min_order: float = 0,
                    expires_days: int = 30, description: str = '') -> Dict:
        """Create a new promo code."""
        code = code.upper().strip()

        if code in self.codes:
            return {'success': False, 'error': f'Code {code} already exists'}

        if discount_type not in ['percentage', 'fixed']:
            return {'success': False, 'error': 'Type must be percentage or fixed'}

        if discount_type == 'percentage' and (value < 1 or value > 50):
            return {'success': False, 'error': 'Percentage must be 1-50%'}

        self.codes[code] = {
            'code': code,
            'type': discount_type,
            'value': value,
            'max_uses': max_uses,
            'used': 0,
            'min_order': min_order,
            'expires': datetime.now() + timedelta(days=expires_days),
            'active': True,
            'description': description or f'{value}{"%" if discount_type == "percentage" else " BDT"} discount',
            'created_at': datetime.now()
        }

        logger.info(f"Promo code created: {code}")
        self._save_data()
        return {'success': True, 'code': code}

    def validate_code(self, code: str, order_total: float = 0) -> Dict:
        """Validate a promo code and calculate discount."""
        code = code.upper().strip()
        promo = self.codes.get(code)

        if not promo:
            return {'valid': False, 'error': 'Invalid promo code'}

        if not promo['active']:
            return {'valid': False, 'error': 'This code is no longer active'}

        if datetime.now() > promo['expires']:
            return {'valid': False, 'error': 'This code has expired'}

        if promo['used'] >= promo['max_uses']:
            return {'valid': False, 'error': 'This code has reached its usage limit'}

        if order_total < promo['min_order']:
            return {
                'valid': False,
                'error': f'Minimum order ৳{promo["min_order"]} required'
            }

        # Calculate discount
        if promo['type'] == 'percentage':
            discount = order_total * (promo['value'] / 100)
        else:
            discount = promo['value']

        # Cap discount at order total
        discount = min(discount, order_total)

        return {
            'valid': True,
            'code': code,
            'discount': discount,
            'final_total': order_total - discount,
            'type': promo['type'],
            'value': promo['value'],
            'description': promo['description']
        }

    def redeem_code(self, code: str, order_id: str, customer: str) -> bool:
        """Mark a code as used."""
        code = code.upper().strip()
        promo = self.codes.get(code)
        if promo:
            promo['used'] += 1
            self.redemptions.append({
                'code': code,
                'order_id': order_id,
                'customer': customer,
                'timestamp': datetime.now()
            })
            self._save_data()
            self._save_redemptions()
            return True
        return False

    def toggle_code(self, code: str) -> Dict:
        """Activate/deactivate a promo code."""
        code = code.upper().strip()
        promo = self.codes.get(code)
        if not promo:
            return {'success': False, 'error': 'Code not found'}

        promo['active'] = not promo['active']
        status = 'activated' if promo['active'] else 'deactivated'
        self._save_data()
        return {'success': True, 'status': status}

    def delete_code(self, code: str) -> bool:
        """Delete a promo code."""
        code = code.upper().strip()
        if code in self.codes:
            del self.codes[code]
            self._save_data()
            return True
        return False

    def get_all_codes(self) -> List[Dict]:
        """Get all promo codes sorted by creation."""
        return sorted(
            self.codes.values(),
            key=lambda x: x.get('created_at', datetime.min),
            reverse=True
        )

    def _save_data(self):
        """Save promo codes to JSON."""
        try:
            # Convert datetime objects to strings
            save_codes = {}
            for k, v in self.codes.items():
                code_data = v.copy()
                if isinstance(code_data.get('expires'), datetime):
                    code_data['expires'] = code_data['expires'].isoformat()
                if isinstance(code_data.get('created_at'), datetime):
                    code_data['created_at'] = code_data['created_at'].isoformat()
                save_codes[k] = code_data
            
            with open(self.promos_file, 'w', encoding='utf-8') as f:
                json.dump(save_codes, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save promo data: {e}")

    def _save_redemptions(self):
        """Save redemptions to separate JSON."""
        try:
            red_file = self.promos_file.replace('.json', '_redemptions.json')
            save_reds = []
            for r in self.redemptions:
                red_data = r.copy()
                if isinstance(red_data.get('timestamp'), datetime):
                    red_data['timestamp'] = red_data['timestamp'].isoformat()
                save_reds.append(red_data)
                
            with open(red_file, 'w', encoding='utf-8') as f:
                json.dump(save_reds, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save redemptions: {e}")

    def load(self):
        """Load data from disk."""
        try:
            if os.path.exists(self.promos_file):
                with open(self.promos_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if v.get('expires'):
                            v['expires'] = datetime.fromisoformat(v['expires'])
                        if v.get('created_at'):
                            v['created_at'] = datetime.fromisoformat(v['created_at'])
                        self.codes[k] = v
            
            red_file = self.promos_file.replace('.json', '_redemptions.json')
            if os.path.exists(red_file):
                with open(red_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for r in data:
                        if r.get('timestamp'):
                            r['timestamp'] = datetime.fromisoformat(r['timestamp'])
                        self.redemptions.append(r)
        except Exception as e:
            logger.error(f"Failed to load promo data: {e}")

    def format_all_codes(self) -> str:
        """Format all promo codes for admin view."""
        codes = self.get_all_codes()
        if not codes:
            return "No promo codes configured."

        text = f"🏷️ *Promo Codes*\n{'━' * 28}\n\n"

        for p in codes:
            status = '🟢' if p['active'] else '🔴'
            expired = datetime.now() > p['expires']
            if expired:
                status = '⏰'

            expires = p['expires'].strftime('%b %d, %Y')

            if p['type'] == 'percentage':
                discount_text = f"{p['value']}% off"
            else:
                discount_text = f"৳{p['value']} off"

            text += (
                f"{status} `{p['code']}`\n"
                f"    {discount_text} | "
                f"Used: {p['used']}/{p['max_uses']} | "
                f"Min: ৳{p['min_order']}\n"
                f"    Expires: {expires}\n\n"
            )

        text += f"📊 Total redemptions: {len(self.redemptions)}"
        return text

    def format_validation_result(self, result: Dict) -> str:
        """Format validation result for user."""
        if not result['valid']:
            return f"❌ {result['error']}"

        return (
            f"✅ *Code Applied!*\n\n"
            f"🏷️ Code: `{result['code']}`\n"
            f"💰 Discount: ৳{result['discount']:,.0f}\n"
            f"📝 {result['description']}\n\n"
            f"💵 New Total: *৳{result['final_total']:,.0f}*"
        )

    def get_status(self) -> str:
        active = sum(1 for c in self.codes.values() if c['active'])
        return f"{active} active / {len(self.codes)} total codes"


# Global instance
promo_engine = PromoCodeEngine()
