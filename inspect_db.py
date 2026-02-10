
from database_enhanced import get_database

def inspect():
    with open("inspect_db_output.txt", "w") as f:
        try:
            db = get_database()
            f.write("Connecting to database...\n")
            
            # Get columns for orders table
            tables = ['orders', 'order_items', 'products']
            for table in tables:
                f.write(f"\nScanning table: {table}\n")
                query = f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position;
                """
                columns = db.fetch_all(query)
                if not columns:
                    f.write(f"No columns found or table '{table}' does not exist.\n")
                for col in columns:
                    f.write(f"- {col['column_name']} ({col['data_type']})\n")

                
        except Exception as e:
            f.write(f"Error: {e}\n")

if __name__ == "__main__":
    inspect()
