"""
src/database.py
manage connection to DuckDB and extract Schema for LLM and formulating them into clear, understandable text to prevent hallucinations and establish the prompting context.
"""

from pathlib import Path
from typing import Dict, List, Any
import duckdb


class DatabaseManager:
    """Database Connection and Metadata Extraction Manager"""

    def __init__(self, db_path: str = "data/analytics.duckdb", read_only: bool = True):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}. Run init_db.py first.")
        self.read_only = read_only

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Open an isolated connection with security verification (Read-Only)."""
        return duckdb.connect(str(self.db_path), read_only=self.read_only)

    def get_schema_context(self) -> str:
        """
        Extracting table and column schemas, along with illustrative samples, in a structured text format for LLMs.
        """
        con = self.get_connection()
        schema_prompt = []

        try:
            # Retrieve table names
            tables = con.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'main';
            """).fetchall()

            for (table_name,) in tables:
                schema_prompt.append(f"Table: {table_name}")
                schema_prompt.append("Columns:")

                # Retrieve column names and their data types.
                columns = con.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}';
                """).fetchall()

                for col_name, data_type in columns:
                    # Retrieving samples of unique values ​​from text columns to avoid hallucinations in filter conditions.
                    sample_str = ""
                    if data_type in ("VARCHAR", "TEXT"):
                        samples = con.execute(f"""
                            SELECT DISTINCT "{col_name}" 
                            FROM "{table_name}" 
                            WHERE "{col_name}" IS NOT NULL 
                            LIMIT 3;
                        """).fetchall()
                        sample_values = [str(s[0]) for s in samples]
                        if sample_values:
                            sample_str = f" | Example values: {sample_values}"

                    schema_prompt.append(f"  - {col_name} ({data_type}){sample_str}")

                schema_prompt.append("") # Empty line between tables

            return "\n".join(schema_prompt).strip()

        finally:
            con.close()

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute an SQL query and return the result as a list of dictionaries."""
        con = self.get_connection()
        try:
            df = con.execute(query).df()
            return df.to_dict(orient="records")
        finally:
            con.close()


if __name__ == "__main__":
    # Schema Extraction Test
    db_manager = DatabaseManager()
    schema_str = db_manager.get_schema_context()
    print("--- Extracted Schema Context for LLM ---\n")
    print(schema_str)