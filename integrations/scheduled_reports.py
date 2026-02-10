"""
Nongor Bot V3 - Scheduled Reports Engine
Auto-generates and sends daily/weekly business reports to admins.
"""

import os
import io
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    logger.info("matplotlib not installed - chart features disabled")


class ScheduledReports:
    """Auto-generate daily/weekly business reports with charts."""

    def __init__(self):
        self.daily_enabled = False
        self.weekly_enabled = False
        self.daily_hour = int(os.getenv('REPORT_DAILY_HOUR', '21'))  # 9 PM
        self.weekly_day = int(os.getenv('REPORT_WEEKLY_DAY', '6'))    # Sunday
        self.running = False
        self.task = None
        self.db = None
        self.last_daily = None
        self.last_weekly = None
        self.reports_sent = 0

    def set_database(self, db):
        self.db = db

    async def start(self, admin_ids: List[int], bot, db=None):
        """Start scheduled report loop."""
        if self.running:
            return
        if db:
            self.db = db
        self.running = True
        self.daily_enabled = True
        self.weekly_enabled = True
        self.task = asyncio.create_task(self._schedule_loop(admin_ids, bot))
        logger.info(f"Scheduled reports started (daily@{self.daily_hour}:00, weekly@day{self.weekly_day})")

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            self.task = None

    async def _schedule_loop(self, admin_ids: List[int], bot):
        """Main scheduling loop - checks every 30 minutes."""
        try:
            while self.running:
                now = datetime.now()

                # Daily report
                if self.daily_enabled and now.hour == self.daily_hour:
                    if self.last_daily is None or self.last_daily.date() < now.date():
                        report = await self.generate_daily_report()
                        await self._send_report(admin_ids, bot, report, "daily")
                        self.last_daily = now
                        self.reports_sent += 1

                # Weekly report (on configured day)
                if self.weekly_enabled and now.weekday() == self.weekly_day and now.hour == self.daily_hour:
                    if self.last_weekly is None or (now - self.last_weekly).days >= 6:
                        report = await self.generate_weekly_report()
                        await self._send_report(admin_ids, bot, report, "weekly")
                        self.last_weekly = now
                        self.reports_sent += 1

                await asyncio.sleep(1800)  # Check every 30 mins
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Schedule loop error: {e}")
        finally:
            self.running = False

    async def generate_daily_report(self) -> Dict:
        """Generate daily business report data."""
        if not self.db:
            return {'text': 'Database not connected', 'chart': None}

        try:
            today = self.db.get_today_stats()
            low_stock = self.db.get_low_stock_items(threshold=5)
            top = self.db.get_top_products(days=1, limit=5)
            status_counts = self.db.get_order_count_by_status()

            orders = today.get('order_count', 0)
            revenue = today.get('total_revenue', 0)
            avg = today.get('avg_order', 0)

            # Status breakdown
            status_text = ""
            for s in (status_counts or []):
                status_text += f"  • {s.get('status', '?')}: {s.get('count', 0)}\n"

            # Top products
            top_text = ""
            for i, p in enumerate((top or [])[:5], 1):
                top_text += f"  {i}. {p.get('product_name', '?')} ({p.get('order_count', 0)} sold)\n"

            # Low stock warning (no products table, skip)
            low_text = ""

            text = (
                f"📊 *DAILY REPORT*\n"
                f"{'━' * 28}\n"
                f"📅 {datetime.now().strftime('%A, %B %d, %Y')}\n\n"
                f"💰 Revenue: *৳{revenue:,.0f}*\n"
                f"📦 Orders: *{orders}*\n"
                f"📈 Avg Order: ৳{avg:,.0f}\n\n"
                f"📋 *Order Status:*\n{status_text}\n"
                f"🏆 *Top Products:*\n{top_text}"
                f"{low_text}\n"
                f"🕐 Generated: {datetime.now().strftime('%I:%M %p')}"
            )

            # Generate chart if available
            chart = None
            if CHARTS_AVAILABLE:
                chart = await self._generate_daily_chart(orders, revenue)

            return {'text': text, 'chart': chart}

        except Exception as e:
            logger.error(f"Daily report generation error: {e}")
            return {'text': f'Report generation failed: {e}', 'chart': None}

    async def generate_weekly_report(self) -> Dict:
        """Generate weekly business report."""
        if not self.db:
            return {'text': 'Database not connected', 'chart': None}

        try:
            weekly = self.db.get_weekly_stats()
            monthly = self.db.get_monthly_stats()
            top = self.db.get_top_products(days=7, limit=5)

            w_orders = weekly.get('order_count', 0)
            w_revenue = weekly.get('total_revenue', 0)
            m_orders = monthly.get('order_count', 0)
            m_revenue = monthly.get('total_revenue', 0)

            top_text = ""
            for i, p in enumerate((top or [])[:5], 1):
                top_text += f"  {i}. {p.get('product_name', '?')} — {p.get('order_count', 0)} sold (৳{p.get('revenue', 0):,.0f})\n"

            # Week vs Month comparison
            week_pct = (w_revenue / m_revenue * 100) if m_revenue > 0 else 0

            text = (
                f"📈 *WEEKLY REPORT*\n"
                f"{'━' * 28}\n"
                f"📅 Week of {(datetime.now() - timedelta(days=7)).strftime('%b %d')} — {datetime.now().strftime('%b %d, %Y')}\n\n"
                f"💰 Revenue: *৳{w_revenue:,.0f}*\n"
                f"📦 Orders: *{w_orders}*\n"
                f"📈 Avg: ৳{weekly.get('avg_order', 0):,.0f}\n\n"
                f"📊 *vs Monthly:*\n"
                f"  Revenue: {week_pct:.0f}% of monthly total\n"
                f"  Monthly total: ৳{m_revenue:,.0f} ({m_orders} orders)\n\n"
                f"🏆 *Top Products This Week:*\n{top_text}\n"
                f"🕐 Generated: {datetime.now().strftime('%I:%M %p')}"
            )

            chart = None
            if CHARTS_AVAILABLE:
                chart = await self._generate_weekly_chart(w_orders, w_revenue, m_orders, m_revenue)

            return {'text': text, 'chart': chart}

        except Exception as e:
            logger.error(f"Weekly report error: {e}")
            return {'text': f'Report generation failed: {e}', 'chart': None}

    async def _generate_daily_chart(self, orders: int, revenue: float) -> Optional[bytes]:
        """Generate a simple daily summary chart."""
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), facecolor='#1a1a2e')

            # Revenue gauge
            ax1.set_facecolor('#1a1a2e')
            ax1.barh(['Revenue'], [revenue], color='#e94560', height=0.4)
            ax1.set_title('Revenue (৳)', color='white', fontsize=12, fontweight='bold')
            ax1.tick_params(colors='white')
            ax1.spines['top'].set_visible(False)
            ax1.spines['right'].set_visible(False)
            ax1.spines['bottom'].set_color('#333')
            ax1.spines['left'].set_color('#333')
            for label in ax1.get_xticklabels() + ax1.get_yticklabels():
                label.set_color('white')

            # Orders count
            ax2.set_facecolor('#1a1a2e')
            ax2.barh(['Orders'], [orders], color='#0f3460', height=0.4)
            ax2.set_title('Orders', color='white', fontsize=12, fontweight='bold')
            ax2.tick_params(colors='white')
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            ax2.spines['bottom'].set_color('#333')
            ax2.spines['left'].set_color('#333')
            for label in ax2.get_xticklabels() + ax2.get_yticklabels():
                label.set_color('white')

            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                       facecolor='#1a1a2e', edgecolor='none')
            plt.close(fig)
            buf.seek(0)
            return buf.getvalue()

        except Exception as e:
            logger.error(f"Chart generation error: {e}")
            return None

    async def _generate_weekly_chart(self, w_orders, w_revenue, m_orders, m_revenue) -> Optional[bytes]:
        """Generate weekly comparison chart."""
        try:
            fig, ax = plt.subplots(figsize=(8, 5), facecolor='#1a1a2e')
            ax.set_facecolor('#1a1a2e')

            categories = ['Revenue (৳K)', 'Orders']
            week_vals = [w_revenue / 1000, w_orders]
            month_vals = [m_revenue / 1000, m_orders]

            x = range(len(categories))
            width = 0.35
            ax.bar([i - width/2 for i in x], week_vals, width, label='This Week', color='#e94560')
            ax.bar([i + width/2 for i in x], month_vals, width, label='This Month', color='#0f3460')

            ax.set_xticks(x)
            ax.set_xticklabels(categories, color='white')
            ax.set_title('Weekly vs Monthly', color='white', fontsize=14, fontweight='bold')
            ax.legend(facecolor='#16213e', edgecolor='#333', labelcolor='white')
            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('#333')

            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                       facecolor='#1a1a2e', edgecolor='none')
            plt.close(fig)
            buf.seek(0)
            return buf.getvalue()

        except Exception as e:
            logger.error(f"Weekly chart error: {e}")
            return None

    async def _send_report(self, admin_ids: List[int], bot, report: Dict, report_type: str):
        """Send report to all admins."""
        for uid in admin_ids:
            try:
                # Send chart first if available
                if report.get('chart'):
                    await bot.send_photo(
                        chat_id=uid,
                        photo=io.BytesIO(report['chart']),
                        caption=f"{'📊' if report_type == 'daily' else '📈'} {report_type.title()} Report Chart"
                    )

                await bot.send_message(
                    chat_id=uid,
                    text=report['text'],
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send {report_type} report to {uid}: {e}")

    async def send_now(self, admin_ids: List[int], bot, report_type: str = 'daily') -> bool:
        """Manually trigger a report."""
        if report_type == 'weekly':
            report = await self.generate_weekly_report()
        else:
            report = await self.generate_daily_report()

        await self._send_report(admin_ids, bot, report, report_type)
        self.reports_sent += 1
        return True

    def get_status(self) -> str:
        if self.running:
            chart_status = "with charts" if CHARTS_AVAILABLE else "text only"
            return f"Active ({chart_status}, {self.reports_sent} sent)"
        return "Inactive"


# Global instance
scheduled_reports = ScheduledReports()
