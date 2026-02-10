
from database_enhanced import get_database

def check():
    with open("pricing_check.txt", "w", encoding="utf-8") as f:
        db = get_database()
        f.write("Checking pricing data...\n")
        try:
            query = """
                SELECT 
                    COUNT(*) as total_rows,
                    COUNT(price) as rows_with_price,
                    COUNT(total_price) as rows_with_total_price,
                    COUNT(total) as rows_with_total
                FROM orders
            """
            stats = db.fetch_one(query)
            f.write(f"Stats: {stats}\n")
            
            query_samples = """
                SELECT product_name, price, total_price, total, quantity
                FROM orders
                WHERE product_name IS NOT NULL
                LIMIT 10
            """
            samples = db.fetch_all(query_samples)
            for s in samples:
                f.write(f"Product: {s['product_name']} | P: {s['price']} | TP: {s['total_price']} | T: {s['total']} | Q: {s['quantity']}\n")
        except Exception as e:
            f.write(f"Error: {e}\n")

if __name__ == "__main__":
    check()
