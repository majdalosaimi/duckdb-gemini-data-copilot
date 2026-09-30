"""
src/init_db.py
Setting up a local DuckDB database with an expanded star schema that simulates hundreds of real-world transactions.
"""

from pathlib import Path
import random
from datetime import datetime, timedelta
import duckdb

DB_PATH = Path("data/analytics.duckdb")


def initialize_database(db_path: Path = DB_PATH, num_orders: int = 500) -> None:
    """Creating tables and injecting extensive, realistic data for sales, customers, and products."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Delete the old file, if it exists, to ensure a clean build and avoid foreign key conflicts.
    if db_path.exists():
        db_path.unlink()
    
    con = duckdb.connect(str(db_path))

    # Controlling randomness to ensure reproducibility 
    random.seed(42)

    # 1. Product Dimensions Table (Dim_Products)
    con.execute("""
    CREATE OR REPLACE TABLE dim_products (
        product_id INTEGER PRIMARY KEY,
        product_name VARCHAR NOT NULL,
        category VARCHAR NOT NULL,
        unit_price DECIMAL(10, 2) NOT NULL
    );
    """)

    products_data = [
        (101, 'Cloud Data Lakehouse Course', 'Training', 299.00),
        (102, 'Enterprise Analytics Suite', 'Software', 1200.00),
        (103, 'AI Model Monitoring Tool', 'Software', 850.00),
        (104, 'Data Strategy Consultation', 'Services', 2500.00),
        (105, 'DuckDB in Production Guide', 'Books', 45.00),
        (106, 'BI Dashboard Masterclass', 'Training', 199.00),
        (107, 'Cloud Migration Assessment', 'Services', 3200.00),
        (108, 'Edge AI Inference Server', 'Hardware', 4500.00),
        (109, 'Automated ETL Connector', 'Software', 600.00),
        (110, 'MLOps Architecture Blueprint', 'Books', 65.00),
    ]

    con.executemany("INSERT INTO dim_products VALUES (?, ?, ?, ?);", products_data)

    # 2. Customer Dimension Table (Dim_Customers)
    con.execute("""
    CREATE OR REPLACE TABLE dim_customers (
        customer_id INTEGER PRIMARY KEY,
        customer_name VARCHAR NOT NULL,
        region VARCHAR NOT NULL,
        industry VARCHAR NOT NULL,
        signup_date DATE NOT NULL
    );
    """)

    customers_data = [
        (1, 'Aramco Energy Lab', 'Eastern', 'Energy', '2025-01-15'),
        (2, 'Riyadh FinTech Hub', 'Central', 'Financial Services', '2025-02-01'),
        (3, 'Red Sea Development', 'Western', 'Tourism & Hospitality', '2025-03-10'),
        (4, 'NEOM Tech Ventures', 'Northern', 'Technology', '2025-04-22'),
        (5, 'Al Rajhi Digital', 'Central', 'Banking', '2025-05-05'),
        (6, 'SABIC Innovation Center', 'Eastern', 'Manufacturing', '2025-06-12'),
        (7, 'Jeddah Port Logistics', 'Western', 'Logistics', '2025-07-01'),
        (8, 'Qiddiya Smart City', 'Central', 'Entertainment', '2025-08-18'),
        (9, 'Asir Tourism Authority', 'Southern', 'Government', '2025-09-04'),
        (10, 'STC Cloud Solutions', 'Central', 'Telecommunications', '2025-10-11'),
        (11, 'Diriyah Gate Tech', 'Central', 'Real Estate', '2025-11-20'),
        (12, 'Yanbu Petrochemicals', 'Western', 'Industrial', '2025-12-05'),
        (13, 'Tabuk Agriculture AI', 'Northern', 'Agriculture', '2026-01-08'),
        (14, 'Dammam Cold Chain', 'Eastern', 'Logistics', '2026-01-25'),
        (15, 'Madinah Smart Mobility', 'Western', 'Transportation', '2026-02-14'),
        (16, 'Najran Health Network', 'Southern', 'Healthcare', '2026-02-28'),
        (17, 'Hail AgriTech Farm', 'Northern', 'Agriculture', '2026-03-15'),
        (18, 'Taif Eco Resort', 'Western', 'Tourism', '2026-04-02'),
        (19, 'Jazan Power Station', 'Southern', 'Energy', '2026-04-20'),
        (20, 'Riyadh Retail Group', 'Central', 'Retail', '2026-05-01'),
    ]

    con.executemany("INSERT INTO dim_customers VALUES (?, ?, ?, ?, ?);", customers_data)

    # 3. Sales Fact Table (Fact_Orders)
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

    # Generating 500 realistic sales transactions across varying time periods.
    start_date = datetime(2025, 6, 1)
    end_date = datetime(2026, 8, 30)
    total_days = (end_date - start_date).days

    orders_data = []
    product_ids = [p[0] for p in products_data]
    customer_ids = [c[0] for c in customers_data]
    discounts_pool = [0.00, 0.00, 0.05, 0.10, 0.15, 0.20]

    for order_idx in range(1, num_orders + 1):
        rand_days = random.randint(0, total_days)
        order_date = (start_date + timedelta(days=rand_days)).strftime("%Y-%m-%d")
        
        # Selecting a customer, product, and quantity
        cust_id = random.choice(customer_ids)
        prod_id = random.choice(product_ids)
        
        # If the product is hardware or a consultation, the quantity is small; if it consists of books or courses, it is larger.
        if prod_id in (104, 107, 108):
            quantity = random.randint(1, 3)
        elif prod_id in (105, 110):
            quantity = random.randint(2, 20)
        else:
            quantity = random.randint(1, 8)

        discount = random.choice(discounts_pool)

        orders_data.append((
            1000 + order_idx,
            order_date,
            cust_id,
            prod_id,
            quantity,
            discount
        ))

    con.executemany("INSERT INTO fact_orders VALUES (?, ?, ?, ?, ?, ?);", orders_data)

    # Print a quick summary for verification.
    orders_count = con.execute("SELECT count(*) FROM fact_orders;").fetchone()[0]
    cust_count = con.execute("SELECT count(*) FROM dim_customers;").fetchone()[0]
    prod_count = con.execute("SELECT count(*) FROM dim_products;").fetchone()[0]

    con.close()
    print(f" Database successfully initialized at: {db_path}")
    print(f" Loaded: {orders_count} Orders, {cust_count} Customers, {prod_count} Products.")


if __name__ == "__main__":
    initialize_database()