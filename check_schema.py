
from database_enhanced import get_database

def check_columns():
    db = get_database()
    print("Checking 'orders' table columns...")
    try:
        # Query to get column names from information_schema
        query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'orders';
        """
        rows = db.fetch_all(query)
        print(f"Found {len(rows)} columns:")
        for row in rows:
            print(f"- {row['column_name']} ({row['data_type']})")
            
        # Also let's inspect one row of data to see values
        print("\nSample Data (First row):")
        data_query = "SELECT * FROM orders LIMIT 1"
        data = db.fetch_all(data_query)
        if data:
            print(data[0])
        else:
            print("No data found")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_columns()
