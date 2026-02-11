import os
import asyncio
from dotenv import load_dotenv
from bot_standard.database import Database

"""
End-to-End Analytics Integration Test
====================================
Verifies: 
1. Website API connection
2. Data merging logic
3. Business Intelligence aggregation
"""

async def test_analytics():
    load_dotenv()
    
    # Connection string
    db_url = os.getenv("NETLIFY_DATABASE_URL")
    if not db_url:
        print("❌ ERROR: NETLIFY_DATABASE_URL not found in .env")
        return

    # Initialize DB
    db = Database(db_url)
    
    print("🧪 Testing Full-Stack Analytics Integration...\n")

    # 1. Test Website API Connectivity
    print("1️⃣  Testing Website API Connection...")
    analytics = await db.get_website_analytics()
    if analytics:
        print(f"✅ SUCCESS: Connected to {os.getenv('WEBSITE_URL')}")
        print(f"   Visitors Today: {analytics.get('today', {}).get('visitors')}")
        print(f"   Page Views: {analytics.get('today', {}).get('pageViews')}")
    else:
        print("❌ FAILED: Could not reach website analytics API.")

    # 2. Test Conversion Logic
    print("\n2️⃣  Testing Conversion Logic...")
    conv = await db.get_conversion_metrics()
    print(f"   Mode: {conv.get('mode')}")
    if conv.get('mode') == 'full_analytics':
        print(f"   Conversion Rate: {conv.get('conversion_rate')}%")
        print(f"   Abandoned Carts: {conv.get('abandoned_carts')}")
    else:
        print("   ⚠️  Running in Database-Only mode.")

    # 3. Test Master BI Method
    print("\n3️⃣  Testing Master Business Intelligence Method...")
    bi = await db.get_business_intelligence()
    if bi:
        print("✅ SUCCESS: BI report generated.")
        print(f"   Revenue Today: ৳{bi['sales']['today'].get('total_revenue', 0):,.2f}")
        print(f"   Top Seller: {bi['products']['top_sellers'][0]['product_name'] if bi['products']['top_sellers'] else 'N/A'}")
    else:
        print("❌ FAILED: BI report could not be generated.")

    print("\n✅ Verification Complete.")

if __name__ == "__main__":
    asyncio.run(test_analytics())
