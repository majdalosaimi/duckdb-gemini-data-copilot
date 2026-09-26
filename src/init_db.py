"""
src/init_db.py
Initiate a local DuckDB database with a Star Schema (Fact & Dimension Tables) to test LLM anatical queries ability.
"""

from pathlib import Path
import duckdb

DB_PATH = Path("data/analytics.duckdb")


def initialize_database(db_path: Path = DB_PATH) -> None:
    """Creating tables and injecting realistic data for sales, customers, and products."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))

    # 1. Products - Dimension Table (Dim_Products)
    con.execute("""
    CREATE OR REPLACE TABLE dim_products (
        product_id INTEGER PRIMARY KEY,
        product_name VARCHAR NOT NULL,
        category VARCHAR NOT NULL,
        unit_price DECIMAL(10, 2) NOT NULL
    );
    """)

    con.execute("""
    INSERT INTO dim_products VALUES
        (101, 'Cloud Data Lakehouse Course', 'Training', 299.00),
        (102, 'Enterprise Analytics Suite', 'Software', 1200.00),
        (103, 'AI Model Monitoring Tool', 'Software', 850.00),
        (104, 'Data Strategy Consultation', 'Services', 2500.00),
        (105, 'DuckDB in Production Guide', 'Books', 45.00);
    """)

    # 2. Customers - Dimension Table (Dim_Customers)
    con.execute("""
    CREATE OR REPLACE TABLE dim_customers (
        customer_id INTEGER PRIMARY KEY,
        customer_name VARCHAR NOT NULL,
        region VARCHAR NOT NULL,
        signup_date DATE NOT NULL
    );
    """)

    con.execute("""
    INSERT INTO dim_customers VALUES
        (1, 'Aramco Energy Lab', 'Eastern', '2025-01-15'),
        (2, 'Riyadh FinTech Hub', 'Central', '2025-02-01'),
        (3, 'Red Sea Development', 'Western', '2025-03-10'),
        (4, 'NEOM Tech Ventures', 'Northern', '2025-04-22'),
        (5, 'Al Rajhi Digital', 'Central', '2025-05-05');
    """)

    # 3. Orders - Fact Table (Fact_Orders)
    con.execute("""
    CREATE OR REPLACE TABLE fact_orders (
        order_id INTEGER PRIMARY KEY,
        order_date DATE NOT NULL,
        customer_id INTEGER REFERENCES dim_customers(customer_id),
        product_id INTEGER REFERENCES dim_products(product_id),
        quantity INTEGER NOT NULL,
        discount DECIMAL(4, 2) DEFAULT 0.00
    );
    """)

    con.execute("""
    INSERT INTO fact_orders VALUES
        (1001, '2026-01-10', 1, 102, 2, 0.10),
        (1002, '2026-01-14', 2, 101, 5, 0.00),
        (1003, '2026-02-03', 3, 104, 1, 0.05),
        (1004, '2026-02-20', 2, 103, 3, 0.15),
        (1005, '2026-03-01', 4, 102, 1, 0.00),
        (1006, '2026-03-15', 5, 101, 10, 0.20),
        (1007, '2026-04-02', 1, 104, 1, 0.00),
        (1008, '2026-04-18', 3, 103, 2, 0.05);
    """)

    con.close()
    print(f" Database successfully initialized at: {db_path}")


if __name__ == "__main__":
    initialize_database()