"""
src/generator.py
Generating structured DuckDB SQL queries via the Gemini API using the modern google-genai library.
"""

import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError
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

    def __init__(self, primary_model: str = "gemini-2.0-flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing. Check your .env file.")

        self.client = genai.Client(api_key=api_key)
        
        self.candidate_models = [
            primary_model,
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite"
        ]

    def _call_model_with_retry(self, model_name: str, prompt: str, max_retries: int = 3):
        """Attempting to connect to the model with exponential backoff to avoid 503 errors."""
        config = types.GenerateContentConfig(
            system_instruction=SQL_SYSTEM_INSTRUCTION,
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=SQLGenerationOutput,
        )

        delay = 2.0
        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                return response.parsed
            except ServerError as e:
                # Error 503 or temporary server issues
                if attempt == max_retries:
                    raise e
                print(f"⚠️ Model {model_name} is busy (503). Retrying in {delay}s (Attempt {attempt}/{max_retries})...")
                time.sleep(delay)
                delay *= 2  # Doubling the waiting period
            except ClientError as e:
                # If the model is unavailable to begin with (404), we do not wait; instead, we move on to the alternative.
                raise e

    def generate(self, user_query: str, schema_context: str) -> SQLGenerationOutput:
        """Submit the request with an automatic switch to an alternative form if congestion persists."""
        prompt = build_sql_prompt(user_query, schema_context)

        last_exception = None
        for model in self.candidate_models:
            try:
                return self._call_model_with_retry(model, prompt)
            except (ServerError, ClientError) as err:
                print(f"🔄 Switching from {model} due to: {err.message if hasattr(err, 'message') else 'Error'}")
                last_exception = err
                continue

        raise RuntimeError(f"All model endpoints failed. Last error: {last_exception}")


if __name__ == "__main__":
    # Generator operation test and query validation
    db_mgr = DatabaseManager()
    schema = db_mgr.get_schema_context()

    generator = SQLGenerator(primary_model="gemini-2.0-flash")
    test_question = "ما هي أعلى 3 منتجات مبيعاً من حيث إجمالي الإيرادات بعد الخصم؟"

    print(f"User Query: {test_question}\n" + "-" * 50)
    result = generator.generate(test_question, schema)

    print("\n--- Generated SQL Query ---")
    print(result.sql_query)
    print("\n--- Logic Explanation ---")
    print(result.explanation)
    print("\n--- Recommended Chart ---")
    print(result.intended_chart_type)