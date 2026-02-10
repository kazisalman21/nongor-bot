
from database_enhanced import get_database
import sys

def inspect():
    with open("data_sample.txt", "w", encoding="utf-8") as f:
        db = get_database()
        f.write("Fetching order samples...\n")
        try:
            query = """
                SELECT order_id, total, total_price, price 
                FROM orders 
                ORDER BY created_at DESC 
                LIMIT 5
            """
            rows = db.fetch_all(query)
            for row in rows:
                line = f"ID: {row['order_id']} | Total: {row['total']} | TotalPrice: {row.get('total_price')} | Price: {row.get('price')}\n"
                f.write(line)
                print(line)
                
        except Exception as e:
            f.write(f"Error: {e}\n")
            print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
