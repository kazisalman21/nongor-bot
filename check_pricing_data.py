
from database_enhanced import get_database

def check():
    db = get_database()
    print("Checking pricing data...")
    query = """
        SELECT 
            COUNT(*) as total_rows,
            COUNT(price) as rows_with_price,
            COUNT(total_price) as rows_with_total_price,
            COUNT(total) as rows_with_total
        FROM orders
    """
    stats = db.fetch_one(query)
    print(f"Stats: {stats}")
    
    query_samples = """
        SELECT product_name, price, total_price, total, quantity
        FROM orders
        WHERE product_name IS NOT NULL
        LIMIT 5
    """
    samples = db.fetch_all(query_samples)
    for s in samples:
        print(f"Product: {s['product_name']} | P: {s['price']} | TP: {s['total_price']} | T: {s['total']} | Q: {s['quantity']}")

if __name__ == "__main__":
    check()
