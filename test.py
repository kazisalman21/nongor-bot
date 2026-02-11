"""
Quick Database Connection Test
===============================
Test if we can connect to your Neon database and see what data exists.
"""

import asyncpg
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("NETLIFY_DATABASE_URL")

async def quick_test():
    print("🔍 Testing connection to Neon database...\n")
    
    try:
        # Connect
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected successfully!\n")
        
        # List tables
        print("📋 Tables in database:")
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        for table in tables:
            table_name = table['table_name']
            
            # Count rows
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                print(f"   ✓ {table_name}: {count} rows")
            except:
                print(f"   ✓ {table_name}")
        
        print("\n📊 Sample Data:\n")
        
        # Try to get sample from common tables
        common_tables = ['orders', 'products', 'customers', 'users']
        
        for table_name in common_tables:
            # Check if table exists
            exists = any(t['table_name'] == table_name for t in tables)
            
            if exists:
                print(f"🔸 {table_name.upper()} (first row):")
                
                # Get first row
                row = await conn.fetchrow(f"SELECT * FROM {table_name} LIMIT 1")
                
                if row:
                    for key, value in dict(row).items():
                        # Truncate long values
                        val_str = str(value)
                        if len(val_str) > 60:
                            val_str = val_str[:57] + "..."
                        print(f"   {key}: {val_str}")
                    print()
                else:
                    print(f"   (Table is empty)\n")
        
        # Get column details for coupons
        if any(t['table_name'] == 'coupons' for t in tables):
            print("📝 COUPONS Table Structure:")
            columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'coupons'
                ORDER BY ordinal_position
            """)
            
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                print(f"   {col['column_name']:<25} {col['data_type']:<15} {nullable}")
        
        await conn.close()
        
        print("\n✅ Test complete!")
        print("\n💡 Next: Share this output with Claude to customize your bot!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Check if database URL is correct")
        print("   - Verify database is accessible")

if __name__ == "__main__":
    asyncio.run(quick_test())