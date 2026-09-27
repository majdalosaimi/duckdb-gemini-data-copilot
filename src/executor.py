"""
src/executor.py
Security verification and DuckDB query execution module with a self-correction loop.
"""

import re
from typing import Dict, Any, List, Optional
import pandas as pd
from pydantic import BaseModel, Field

from src.database import DatabaseManager
from src.generator import SQLGenerator, SQLGenerationOutput


class ExecutionResult(BaseModel):
    """An object representing the final result of the execution."""
    success: bool
    sql_query: str
    data: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    error_message: Optional[str] = None
    retries_used: int = 0
    intended_chart_type: str = "table"
    explanation: str = ""


class SafeSQLExecutor:
    """A secure SQL query executor that checks for forbidden words and handles errors automatically."""

    # List of forbidden words to prevent any tampering with the database.
    FORBIDDEN_KEYWORDS = [
        r"\bDROP\b",
        r"\bDELETE\b",
        r"\bINSERT\b",
        r"\bUPDATE\b",
        r"\bALTER\b",
        r"\bCREATE\b",
        r"\bTRUNCATE\b",
        r"\bGRANT\b",
        r"\bREVOKE\b",
        r"\bCOPY\b",
        r"\bATTACH\b",
        r"\bDETACH\b",
    ]

    def __init__(self, db_manager: DatabaseManager, generator: SQLGenerator, max_retries: int = 2):
        self.db_manager = db_manager
        self.generator = generator
        self.max_retries = max_retries

    def validate_sql_security(self, query: str) -> None:
        """Verifying that the query is purely retrieval-based and complies with security standards."""
        cleaned_query = query.strip().upper()

        # Ensure that the query starts with SELECT or WITH (CTEs).
        if not (cleaned_query.startswith("SELECT") or cleaned_query.startswith("WITH")):
            raise PermissionError("Security Violation: Only SELECT or WITH queries are allowed.")

        # Verifying that the query is free of prohibited words.
        for pattern in self.FORBIDDEN_KEYWORDS:
            if re.search(pattern, cleaned_query, re.IGNORECASE):
                raise PermissionError(f"Security Violation: Query contains prohibited keyword matching {pattern}.")

    def _execute_raw(self, query: str) -> List[Dict[str, Any]]:
        """Run the query in read-only mode and retrieve the results as a dictionary."""
        self.validate_sql_security(query)
        return self.db_manager.execute_query(query)

    def run_with_self_healing(self, user_query: str, schema_context: str) -> ExecutionResult:
        """
        Generating and executing the query with retries, and passing errors to the form upon failure.
        """
        current_user_query = user_query
        last_error = None
        retries = 0

        # Initial generation
        generated_output: SQLGenerationOutput = self.generator.generate(
            user_query=current_user_query,
            schema_context=schema_context
        )

        for attempt in range(self.max_retries + 1):
            try:
                # Security Verification and Execution within DuckDB
                data = self._execute_raw(generated_output.sql_query)
                return ExecutionResult(
                    success=True,
                    sql_query=generated_output.sql_query,
                    data=data,
                    row_count=len(data),
                    retries_used=retries,
                    intended_chart_type=generated_output.intended_chart_type,
                    explanation=generated_output.explanation,
                )

            except Exception as err:
                last_error = str(err)
                print(f"⚠️ Query execution failed on attempt {attempt + 1}: {last_error}")

                if attempt == self.max_retries:
                    break

                retries += 1
                # Constructing a self-correction prompt by attaching the original error message.
                correction_prompt = f"""
                    The previous DuckDB SQL query failed with an execution error.
                    Original User Request: {user_query}
                    Failed SQL Query: {generated_output.sql_query}
                    Exact Error Message from Database: {last_error}

                    Fix the SQL query syntax, ensure all referenced columns and tables match the schema, and regenerate.
                    """
                print("🔄 Triggering LLM self-correction loop...")
                generated_output = self.generator.generate(
                    user_query=correction_prompt,
                    schema_context=schema_context
                )

        return ExecutionResult(
            success=False,
            sql_query=generated_output.sql_query,
            error_message=last_error,
            retries_used=retries,
            intended_chart_type=generated_output.intended_chart_type,
            explanation=generated_output.explanation,
        )


if __name__ == "__main__":
    db_mgr = DatabaseManager()
    schema = db_mgr.get_schema_context()
    gen = SQLGenerator(primary_model="gemini-2.0-flash")
    executor = SafeSQLExecutor(db_manager=db_mgr, generator=gen)

    # # 1. Test a complex, valid query (calculating total sales including customer name and product name)
    test_q = "احسب إجمالي مبيعات كل عميل بعد الخصم ورتبهم من الأكثر إنفاقاً إلى الأقل"
    print(f"Testing Query: {test_q}\n" + "=" * 60)
    res = executor.run_with_self_healing(test_q, schema)

    if res.success:
        print(" Execution Successful!")
        print(f"SQL Used:\n{res.sql_query}")
        print(f"\nRetries: {res.retries_used}")
        print(f"Rows Returned: {res.row_count}")
        print("\nResults Sample:")
        print(pd.DataFrame(res.data))
    else:
        print(f" Execution Failed: {res.error_message}")