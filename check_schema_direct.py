
from database_enhanced import get_database
import sys

def check_columns():
    with open("schema_out.txt", "w", encoding="utf-8") as f:
        try:
            db = get_database()
            f.write("Fetching schema info...\n")
            
            # Query for columns (products)
            f.write("Checking 'products' table...\n")
            query = "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'products'"
            rows = db.fetch_all(query)
            f.write(f"Columns ({len(rows)}):\n")
            for row in rows:
                f.write(f"- {row['column_name']} ({row['data_type']})\n")

            # Query for columns (order_items)
            f.write("\nChecking 'order_items' table...\n")
            query = "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'order_items'"
            rows = db.fetch_all(query)
            f.write(f"Columns ({len(rows)}):\n")
            for row in rows:
                f.write(f"- {row['column_name']} ({row['data_type']})\n")

                
        except Exception as e:
            f.write(f"Error: {e}")

if __name__ == "__main__":
    check_columns()
