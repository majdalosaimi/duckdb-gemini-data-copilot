"""
src/generator.py
Generating structured DuckDB SQL queries via the Gemini API using the modern google-genai library.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from src.database import DatabaseManager
from src.prompts import SQL_SYSTEM_INSTRUCTION, build_sql_prompt

load_dotenv()


class SQLGenerationOutput(BaseModel):
    """The strict schema for query generation results."""
    sql_query: str = Field(
        description="Clean executable DuckDB SQL query. Must be read-only and free of markdown syntax."
    )
    explanation: str = Field(
        description="Brief explanation of the SQL logic, join conditions, and calculations used."
    )
    intended_chart_type: str = Field(
        description="Best visualization type for this data: 'bar', 'line', 'scatter', or 'table'."
    )


class SQLGenerator:
    """A class responsible for managing interaction with the Gemini API to generate data queries."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing. Set it in your .env file.")

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def generate(self, user_query: str, schema_context: str) -> SQLGenerationOutput:
        """Send the question and the model schema, and retrieve a structured, Pydantic-validated response."""
        prompt = build_sql_prompt(user_query, schema_context)

        config = types.GenerateContentConfig(
            system_instruction=SQL_SYSTEM_INSTRUCTION,
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=SQLGenerationOutput,
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )

        # `response.parsed` directly contains Pydantic object.
        return response.parsed


if __name__ == "__main__":
    # Generator operation test and query validation
    db_mgr = DatabaseManager()
    schema = db_mgr.get_schema_context()

    generator = SQLGenerator()
    test_question = "ما هي أعلى 3 منتجات مبيعاً من حيث إجمالي الإيرادات بعد الخصم؟"

    print(f"User Query: {test_question}\n" + "-" * 50)
    result = generator.generate(test_question, schema)

    print("\n--- Generated SQL Query ---")
    print(result.sql_query)
    print("\n--- Logic Explanation ---")
    print(result.explanation)
    print("\n--- Recommended Chart ---")
    print(result.intended_chart_type)