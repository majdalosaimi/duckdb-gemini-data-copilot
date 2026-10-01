"""
src/visualizer.py
Generating interactive charts using Plotly and drafting executive analysis of the results using Gemini.
"""

from typing import List, Dict, Any, Optional
import os
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError
from dotenv import load_dotenv

load_dotenv()


class VisualizerAndSynthesizer:
    """Responsible for deriving analytical insights and visualizing data."""

    def __init__(self, primary_model: str = "gemini-3.8-flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing. Check your .env file.")
        self.client = genai.Client(api_key=api_key)
        self.candidate_models = [primary_model, "gemini-3.5-flash-lite"]

    def _prepare_data_context(self, df: pd.DataFrame, threshold: int = 30) -> str:
        """
        Adaptive data context preparation:
        - If the number of rows ≤ threshold: The entire table is passed.
        - If the number of rows > threshold: A statistical summary is passed, along with the top and bottom rows.
        """
        total_rows = len(df)

        if total_rows <= threshold:
            return f"Full Result Set ({total_rows} rows):\n" + df.to_string(index=False)

        # Preparing the statistical summary for numerical columns
        numeric_cols = df.select_dtypes(include=["number"])
        summary_stats = ""
        if not numeric_cols.empty:
            summary_stats = f"\nStatistical Summary (Key Metrics):\n{numeric_cols.describe().to_string()}\n"

        top_rows = df.head(5).to_string(index=False)
        bottom_rows = df.tail(5).to_string(index=False)

        return f"""
                Dataset Dimensions: Total of {total_rows} rows returned.
                {summary_stats}
                Top 5 Sample Records:
                {top_rows}

                Bottom 5 Sample Records:
                {bottom_rows}
                """

    def synthesize_insights(self, user_query: str, data: List[Dict[str, Any]]) -> str:
        """Translating numerical outputs into concise analytical conclusions and recommendations for decision-makers."""
        if not data:
            return "لم يتم العثور على سجلات تطابق شروط الاستعلام المطلوبة."

        df = pd.DataFrame(data)
        data_context = self._prepare_data_context(df, threshold=30)

        prompt = f"""
                You are an Executive Senior Data Analyst.
                Translate the following query results into a concise, professional executive briefing.

                User Question: {user_query}

                Extracted Data Context:
                {data_context}

                Rules:
                1. Provide a direct, assertive answer in 1-2 sharp sentences.
                2. Highlight 2-3 key quantitative findings (use bullet points with percentages, ranks, or totals).
                3. Conclude with one actionable business recommendation.
                4. Respond in the same language as the user's question (Arabic if Arabic, English if English).
                """

        for model in self.candidate_models:
            delay = 2.0
            for attempt in range(1, 4):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.2),
                    )
                    return response.text.strip()
                except ServerError:
                    time.sleep(delay)
                    delay *= 2
                except ClientError:
                    break

        return "تعذر صياغة الملخص التحليلي بسبب ضغط مؤقت على الخوادم."

    def create_figure(
        self, data: List[Dict[str, Any]], chart_type: str = "bar"
    ) -> Optional[go.Figure]:
        """Create an interactive chart object using Plotly based on the column structure."""
        if not data:
            return None

        df = pd.DataFrame(data)
        if len(df.columns) < 2:
            return None

        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        non_numeric_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

        if not numeric_cols:
            return None

        x_col = non_numeric_cols[0] if non_numeric_cols else df.columns[0]
        y_col = numeric_cols[0]

        template_style = "plotly_white"

        if chart_type == "bar":
            fig = px.bar(
                df,
                x=x_col,
                y=y_col,
                title=f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
                text_auto=".2s",
                template=template_style,
            )
            fig.update_layout(xaxis_tickangle=-30)

        elif chart_type == "line":
            fig = px.line(
                df,
                x=x_col,
                y=y_col,
                markers=True,
                title=f"Trend of {y_col.replace('_', ' ').title()} across {x_col.replace('_', ' ').title()}",
                template=template_style,
            )

        elif chart_type == "scatter":
            secondary_y = numeric_cols[1] if len(numeric_cols) > 1 else y_col
            fig = px.scatter(
                df,
                x=x_col,
                y=secondary_y,
                size=y_col if len(numeric_cols) > 1 else None,
                hover_data=df.columns,
                template=template_style,
            )
        else:
            return None

        fig.update_layout(
            margin=dict(l=40, r=40, t=50, b=40),
            hovermode="closest",
        )
        return fig


if __name__ == "__main__":
    from src.database import DatabaseManager
    from src.generator import SQLGenerator
    from src.executor import SafeSQLExecutor

    db_mgr = DatabaseManager()
    schema = db_mgr.get_schema_context()
    gen = SQLGenerator(primary_model="gemini-3.8-flash")
    executor = SafeSQLExecutor(db_mgr, gen)
    viz = VisualizerAndSynthesizer(primary_model="gemini-3.8-flash")

    # Run a query that returns more than 30 rows to verify the statistical summary.
    query = "اعرض قائمة بكافة المعاملات مع أسماء العملاء والمبالغ"
    exec_res = executor.run_with_self_healing(query, schema)

    if exec_res.success:
        print(f"Total Rows Fetched: {exec_res.row_count}")
        insights = viz.synthesize_insights(query, exec_res.data)
        print("\n--- Executive Summary (Generated via Adaptive Context) ---")
        print(insights)