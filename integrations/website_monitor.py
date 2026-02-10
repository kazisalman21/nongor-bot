"""
Nongor Bot V3 - Website Uptime Monitor
Background monitoring with admin alerts for downtime/recovery.
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class WebsiteMonitor:
    """Website uptime monitoring with Telegram alerts."""

    def __init__(self):
        self.website_url = os.getenv('WEBSITE_URL', 'https://nongor-brand.vercel.app/')
        self.check_interval = int(os.getenv('MONITOR_INTERVAL_SECONDS', '300'))
        self.timeout = int(os.getenv('WEBSITE_CHECK_TIMEOUT', '10'))

        self.enabled = False
        self.running = False
        self.task = None

        # State
        self.last_check = None
        self.last_status = None
        self.last_error = None
        self.last_response_time = None
        self.downtime_count = 0
        self.uptime_checks = 0
        self.total_checks = 0
        self.history: List[Dict] = []  # Last 20 checks

    async def check_website(self) -> Dict:
        """Perform a single website health check."""
        if not REQUESTS_AVAILABLE:
            return {'status': 'unknown', 'error': 'requests library not installed'}

        try:
            import time
            start = time.time()
            response = requests.get(
                self.website_url,
                timeout=self.timeout,
                allow_redirects=True
            )
            elapsed = round(time.time() - start, 2)

            result = {
                'status': 'up' if response.status_code == 200 else 'degraded',
                'status_code': response.status_code,
                'response_time': elapsed,
                'timestamp': datetime.now(),
                'error': None
            }

        except requests.exceptions.Timeout:
            result = {
                'status': 'down',
                'status_code': None,
                'response_time': None,
                'timestamp': datetime.now(),
                'error': 'Connection Timeout'
            }
        except requests.exceptions.ConnectionError:
            result = {
                'status': 'down',
                'status_code': None,
                'response_time': None,
                'timestamp': datetime.now(),
                'error': 'Connection Error'
            }
        except Exception as e:
            result = {
                'status': 'down',
                'status_code': None,
                'response_time': None,
                'timestamp': datetime.now(),
                'error': str(e)
            }

        # Update state
        self.last_check = result['timestamp']
        self.last_response_time = result.get('response_time')
        self.last_error = result.get('error')
        self.total_checks += 1

        if result['status'] == 'up':
            self.uptime_checks += 1

        # Keep last 20 checks
        self.history.append(result)
        if len(self.history) > 20:
            self.history.pop(0)

        return result

    async def start_monitoring(self, admin_ids: List[int], bot) -> bool:
        """Start background monitoring loop."""
        if self.running:
            return False

        self.enabled = True
        self.running = True
        self.task = asyncio.create_task(
            self._monitoring_loop(admin_ids, bot)
        )
        logger.info(f"Website monitoring started (interval: {self.check_interval}s)")
        return True

    async def stop_monitoring(self) -> bool:
        """Stop background monitoring."""
        self.enabled = False
        self.running = False
        if self.task:
            self.task.cancel()
            self.task = None
        logger.info("Website monitoring stopped")
        return True

    async def _monitoring_loop(self, admin_ids: List[int], bot):
        """Background monitoring loop with alerts."""
        try:
            while self.enabled:
                result = await self.check_website()
                previous = self.last_status
                current = result['status']

                # Detect status changes
                if previous is not None and previous != current:
                    if current == 'down':
                        self.downtime_count += 1
                        msg = (
                            "🚨 *WEBSITE DOWN!*\n"
                            f"{'━' * 25}\n\n"
                            f"🌐 URL: `{self.website_url}`\n"
                            f"❌ Error: {result.get('error', 'Unknown')}\n"
                            f"🕐 {datetime.now().strftime('%H:%M:%S')}\n"
                            f"⚠️ Total Downtimes: {self.downtime_count}"
                        )
                        await self._alert_admins(admin_ids, bot, msg)

                    elif previous == 'down' and current == 'up':
                        msg = (
                            "✅ *Website Recovered!*\n"
                            f"{'━' * 25}\n\n"
                            f"🌐 URL: `{self.website_url}`\n"
                            f"⚡ Response: {result.get('response_time', '?')}s\n"
                            f"🕐 {datetime.now().strftime('%H:%M:%S')}"
                        )
                        await self._alert_admins(admin_ids, bot, msg)

                self.last_status = current
                await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}")
        finally:
            self.running = False

    async def _alert_admins(self, admin_ids: List[int], bot, message: str):
        """Send alert to all admin users."""
        for uid in admin_ids:
            try:
                await bot.send_message(
                    chat_id=uid, text=message, parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to alert admin {uid}: {e}")

    def get_uptime_percentage(self) -> float:
        """Calculate uptime percentage."""
        if self.total_checks == 0:
            return 100.0
        return round((self.uptime_checks / self.total_checks) * 100, 1)

    def format_status_message(self) -> str:
        """Format current monitoring status for Telegram."""
        status_emoji = {
            'up': '🟢', 'degraded': '🟡', 'down': '🔴', None: '⚪'
        }

        uptime = self.get_uptime_percentage()
        uptime_bar = '█' * int(uptime / 10) + '░' * (10 - int(uptime / 10))

        last_check_str = self.last_check.strftime('%H:%M:%S') if self.last_check else 'Never'
        response_str = f"{self.last_response_time}s" if self.last_response_time else 'N/A'

        return (
            f"🌐 *Website Monitor*\n"
            f"{'━' * 25}\n\n"
            f"URL: `{self.website_url}`\n"
            f"Status: {status_emoji.get(self.last_status, '⚪')} *{(self.last_status or 'Unknown').upper()}*\n"
            f"Response: {response_str}\n\n"
            f"Uptime: [{uptime_bar}] {uptime}%\n"
            f"Total Checks: {self.total_checks}\n"
            f"Downtimes: {self.downtime_count}\n"
            f"Last Check: {last_check_str}\n\n"
            f"Monitoring: {'🟢 ON' if self.running else '🔴 OFF'}\n"
            f"Interval: {self.check_interval}s"
        )

    def get_status(self) -> str:
        """Short status string."""
        if self.running:
            return f"Active (checking every {self.check_interval}s)"
        return "Inactive"


# Global instance
website_monitor = WebsiteMonitor()
