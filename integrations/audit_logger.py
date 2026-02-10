"""
Nongor Bot V3 - Audit Logger
Track all admin actions for accountability and security.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque

logger = logging.getLogger(__name__)


class AuditLogger:
    """Track and log all admin actions with timestamps."""

    def __init__(self, max_entries: int = 500):
        self.entries: deque = deque(maxlen=max_entries)
        self.log_file = os.getenv('AUDIT_LOG_FILE', 'audit.log')
        self.file_logging = True

        # Action categories
        self.categories = {
            'auth': '🔐',
            'order': '📦',
            'export': '📤',
            'broadcast': '📢',
            'monitor': '🌐',
            'promo': '🏷️',
            'settings': '⚙️',
            'crm': '👥',
            'report': '📊',
            'system': '🖥️',
        }

    def log(self, admin_id: int, admin_name: str, action: str,
            category: str = 'system', details: str = '', success: bool = True):
        """Log an admin action."""
        entry = {
            'timestamp': datetime.now(),
            'admin_id': admin_id,
            'admin_name': admin_name,
            'action': action,
            'category': category,
            'details': details,
            'success': success,
            'emoji': self.categories.get(category, '📝')
        }

        self.entries.append(entry)

        # Write to file
        if self.file_logging:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    log_line = (
                        f"[{entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}] "
                        f"{'OK' if success else 'FAIL'} | "
                        f"{admin_name} ({admin_id}) | "
                        f"{category.upper()}: {action}"
                        f"{f' | {details}' if details else ''}\n"
                    )
                    f.write(log_line)
            except Exception as e:
                logger.error(f"Audit file write error: {e}")

        log_level = logging.INFO if success else logging.WARNING
        logger.log(log_level, f"AUDIT: {admin_name} -> {action} [{category}]")

    def get_recent(self, limit: int = 20, category: str = None,
                   admin_id: int = None) -> List[Dict]:
        """Get recent audit entries with optional filters."""
        entries = list(self.entries)

        if category:
            entries = [e for e in entries if e['category'] == category]

        if admin_id:
            entries = [e for e in entries if e['admin_id'] == admin_id]

        return list(reversed(entries))[:limit]

    def format_recent_logs(self, limit: int = 15, category: str = None) -> str:
        """Format recent logs for Telegram display."""
        entries = self.get_recent(limit=limit, category=category)

        if not entries:
            return "📋 No audit entries found."

        text = f"📋 *Audit Log*\n{'━' * 28}\n\n"

        for e in entries:
            ts = e['timestamp'].strftime('%m/%d %H:%M')
            status = '✅' if e['success'] else '❌'
            text += (
                f"{e['emoji']} {status} `{ts}` — *{e['admin_name']}*\n"
                f"    {e['action']}"
                f"{f' ({e['details'][:40]})' if e.get('details') else ''}\n\n"
            )

        text += f"📊 Total entries: {len(self.entries)}"
        return text

    def get_admin_summary(self, admin_id: int) -> Dict:
        """Get action summary for a specific admin."""
        entries = [e for e in self.entries if e['admin_id'] == admin_id]

        category_counts = {}
        for e in entries:
            cat = e['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            'total_actions': len(entries),
            'categories': category_counts,
            'last_action': entries[-1] if entries else None,
            'success_rate': (
                sum(1 for e in entries if e['success']) / len(entries) * 100
                if entries else 100
            )
        }

    def get_status(self) -> str:
        return f"{len(self.entries)} entries logged"


# Global instance
audit_logger = AuditLogger()
