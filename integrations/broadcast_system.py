"""
Nongor Bot V3 - Broadcast System
Send mass messages to users with targeting and scheduling.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BroadcastSystem:
    """Mass messaging with segmentation for Telegram."""

    def __init__(self):
        self.history: List[Dict] = []
        self.total_sent = 0
        self.total_failed = 0

    async def broadcast(self, bot, user_ids: List[int], message: str,
                       parse_mode: str = 'Markdown',
                       delay: float = 0.05) -> Dict:
        """
        Send a message to multiple users.
        
        Args:
            bot: Telegram bot instance
            user_ids: List of user IDs to message
            message: Message text
            parse_mode: Markdown or HTML
            delay: Delay between messages (Telegram rate limit safety)
        """
        sent = 0
        failed = 0
        blocked = 0
        errors = []

        for uid in user_ids:
            try:
                await bot.send_message(
                    chat_id=uid,
                    text=message,
                    parse_mode=parse_mode
                )
                sent += 1
            except Exception as e:
                error_str = str(e).lower()
                if 'blocked' in error_str or 'deactivated' in error_str:
                    blocked += 1
                else:
                    failed += 1
                    if len(errors) < 5:
                        errors.append(f"{uid}: {str(e)[:50]}")

            await asyncio.sleep(delay)

        result = {
            'total': len(user_ids),
            'sent': sent,
            'failed': failed,
            'blocked': blocked,
            'timestamp': datetime.now(),
            'preview': message[:100]
        }

        self.total_sent += sent
        self.total_failed += failed
        self.history.append(result)
        if len(self.history) > 50:
            self.history.pop(0)

        logger.info(
            f"Broadcast: {sent}/{len(user_ids)} sent, "
            f"{failed} failed, {blocked} blocked"
        )

        return result

    async def broadcast_photo(self, bot, user_ids: List[int],
                              photo, caption: str = "",
                              delay: float = 0.05) -> Dict:
        """Send a photo to multiple users."""
        sent = 0
        failed = 0

        for uid in user_ids:
            try:
                await bot.send_photo(
                    chat_id=uid,
                    photo=photo,
                    caption=caption,
                    parse_mode='Markdown'
                )
                sent += 1
            except Exception:
                failed += 1

            await asyncio.sleep(delay)

        result = {
            'total': len(user_ids),
            'sent': sent,
            'failed': failed,
            'timestamp': datetime.now(),
            'type': 'photo'
        }

        self.total_sent += sent
        self.history.append(result)
        return result

    def format_broadcast_result(self, result: Dict) -> str:
        """Format broadcast result for Telegram."""
        success_rate = (result['sent'] / result['total'] * 100) if result['total'] > 0 else 0

        return (
            f"📢 *Broadcast Complete*\n"
            f"{'━' * 25}\n\n"
            f"📨 Total: {result['total']}\n"
            f"✅ Sent: {result['sent']}\n"
            f"❌ Failed: {result.get('failed', 0)}\n"
            f"🚫 Blocked: {result.get('blocked', 0)}\n\n"
            f"📊 Success Rate: {success_rate:.0f}%\n"
            f"🕐 {result['timestamp'].strftime('%I:%M %p')}"
        )

    def get_broadcast_history(self, limit: int = 10) -> str:
        """Format recent broadcast history."""
        if not self.history:
            return "No broadcasts sent yet."

        text = f"📢 *Broadcast History*\n{'━' * 25}\n\n"

        for b in reversed(self.history[-limit:]):
            ts = b['timestamp'].strftime('%m/%d %H:%M')
            text += (
                f"📨 {ts} — {b['sent']}/{b['total']} sent"
                f"{' (photo)' if b.get('type') == 'photo' else ''}\n"
            )

        text += f"\n📊 Total: {self.total_sent} sent, {self.total_failed} failed"
        return text

    def get_status(self) -> str:
        return f"Ready ({self.total_sent} total sent, {len(self.history)} broadcasts)"


# Global instance
broadcast_system = BroadcastSystem()
