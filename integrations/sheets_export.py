"""
Nongor Bot V3 - Google Sheets Export
Export orders, sales analytics, and inventory data to Google Sheets.
"""

import os
import io
import csv
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Try importing Google APIs
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    SHEETS_API_AVAILABLE = True
except ImportError:
    SHEETS_API_AVAILABLE = False
    logger.warning("Google API packages not installed. Install with: pip install google-auth google-api-python-client")


class SheetsExporter:
    """Export business data to Google Sheets with auto-formatting."""

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    def __init__(self):
        self.credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', '')
        self.spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '')
        self.enabled = False
        self.service = None

        if SHEETS_API_AVAILABLE and self.credentials_file and self.spreadsheet_id:
            try:
                if os.path.exists(self.credentials_file):
                    creds = service_account.Credentials.from_service_account_file(
                        self.credentials_file, scopes=self.SCOPES
                    )
                    self.service = build('sheets', 'v4', credentials=creds)
                    self.enabled = True
                    logger.info("Google Sheets exporter initialized")
                else:
                    logger.info(f"Sheets credentials file not found: {self.credentials_file}")
            except Exception as e:
                logger.error(f"Failed to initialize Sheets API: {e}")
        else:
            logger.info("Google Sheets export disabled - missing config or packages")

    def _write_to_sheet(self, range_name: str, values: List[List[Any]], 
                         clear_first: bool = True) -> Dict:
        """Write data to a Google Sheet range."""
        if not self.enabled:
            return {'success': False, 'error': 'Sheets API not configured'}

        try:
            sheet = self.service.spreadsheets()

            # Clear existing data
            if clear_first:
                sheet.values().clear(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name
                ).execute()

            # Write new data
            body = {'values': values}
            result = sheet.values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()

            updated = result.get('updatedCells', 0)
            logger.info(f"Sheets export: {updated} cells updated in {range_name}")

            return {
                'success': True,
                'updated_cells': updated,
                'range': range_name,
                'rows': len(values)
            }

        except Exception as e:
            logger.error(f"Sheets write error: {e}")
            return {'success': False, 'error': str(e)}

    def export_orders(self, orders: List[Dict], sheet_name: str = "Orders") -> Dict:
        """Export orders to a Google Sheet tab."""
        if not orders:
            return {'success': False, 'error': 'No orders to export'}

        # Header row
        headers = [
            'Order ID', 'Date', 'Customer', 'Phone', 'Email',
            'Product', 'Size', 'Quantity', 'Total (BDT)',
            'Status', 'Address', 'District'
        ]

        rows = [headers]
        for order in orders:
            created = order.get('created_at', '')
            if hasattr(created, 'strftime'):
                created = created.strftime('%Y-%m-%d %H:%M')

            rows.append([
                str(order.get('order_id', '')),
                str(created),
                order.get('customer_name', ''),
                order.get('phone', ''),
                order.get('customer_email', ''),
                order.get('product_name', ''),
                order.get('size', ''),
                str(order.get('quantity', 1)),
                str(order.get('total') or order.get('total_price') or 0),
                order.get('status', 'Pending'),
                order.get('address', ''),
                order.get('district', '')
            ])

        return self._write_to_sheet(f"{sheet_name}!A1", rows)

    def export_sales_analytics(self, stats: Dict, sheet_name: str = "Analytics") -> Dict:
        """Export sales analytics summary."""
        rows = [
            ['Nongor Sales Analytics', '', '', datetime.now().strftime('%Y-%m-%d %H:%M')],
            [],
            ['Metric', 'Today', 'This Week', 'This Month'],
            [
                'Total Orders',
                str(stats.get('today_orders', 0)),
                str(stats.get('week_orders', 0)),
                str(stats.get('month_orders', 0))
            ],
            [
                'Revenue (BDT)',
                str(stats.get('today_revenue', 0)),
                str(stats.get('week_revenue', 0)),
                str(stats.get('month_revenue', 0))
            ],
            [
                'Avg Order Value',
                str(stats.get('today_avg', 0)),
                str(stats.get('week_avg', 0)),
                str(stats.get('month_avg', 0))
            ],
            [],
            ['Top Products', 'Units Sold', 'Revenue'],
        ]

        top_products = stats.get('top_products', [])
        for p in top_products:
            rows.append([
                p.get('name', 'Unknown'),
                str(p.get('units', 0)),
                str(p.get('revenue', 0))
            ])

        return self._write_to_sheet(f"{sheet_name}!A1", rows)

    def export_inventory(self, products: List[Dict], sheet_name: str = "Inventory") -> Dict:
        """Export current inventory to Google Sheets."""
        headers = ['Product ID', 'Product Name', 'Size', 'Stock', 'Price (BDT)', 'Status']
        rows = [headers]

        for p in products:
            stock = p.get('stock', 0)
            status = 'Out of Stock' if stock == 0 else ('Low Stock' if stock <= 5 else 'In Stock')

            rows.append([
                str(p.get('id', '')),
                p.get('name', ''),
                p.get('size', ''),
                str(stock),
                str(p.get('price', 0)),
                status
            ])

        return self._write_to_sheet(f"{sheet_name}!A1", rows)

    def generate_csv_report(self, orders: List[Dict]) -> Optional[bytes]:
        """Generate CSV file bytes (for Telegram file sending when Sheets isn't configured)."""
        if not orders:
            return None

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'Order ID', 'Date', 'Customer', 'Phone', 'Product',
            'Size', 'Qty', 'Total', 'Status', 'Address'
        ])

        for order in orders:
            created = order.get('created_at', '')
            if hasattr(created, 'strftime'):
                created = created.strftime('%Y-%m-%d %H:%M')

            writer.writerow([
                order.get('order_id', ''),
                created,
                order.get('customer_name', ''),
                order.get('phone', ''),
                order.get('product_name', ''),
                order.get('size', ''),
                order.get('quantity', 1),
                order.get('total') or order.get('total_price') or 0,
                order.get('status', 'Pending'),
                order.get('address', '')
            ])

        csv_bytes = output.getvalue().encode('utf-8-sig')  # BOM for Excel compatibility
        output.close()
        return csv_bytes

    def get_status(self) -> str:
        """Return sheets service status string."""
        if not SHEETS_API_AVAILABLE:
            return "Disabled (google-api packages not installed)"
        if not self.credentials_file:
            return "Disabled (no credentials file)"
        if not self.spreadsheet_id:
            return "Disabled (no spreadsheet ID)"
        if self.enabled:
            return f"Active (Sheet: ...{self.spreadsheet_id[-8:]})"
        return "Error initializing"


# Global instance
sheets_exporter = SheetsExporter()
