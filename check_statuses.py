
from database_enhanced import get_database

def check_statuses():
    with open("status_check.txt", "w", encoding="utf-8") as f:
        try:
            db = get_database()
            query = "SELECT DISTINCT status FROM orders"
            rows = db.fetch_all(query)
            f.write("Order Statuses:\n")
            for row in rows:
                f.write(f"- {row['status']}\n")
        except Exception as e:
            f.write(f"Error: {e}")

if __name__ == "__main__":
    check_statuses()
