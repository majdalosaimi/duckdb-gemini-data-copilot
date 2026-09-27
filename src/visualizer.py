"""
src/visualizer.py
Generating interactive charts using Plotly and drafting executive analysis of the results using Gemini.
"""

from typing import List, Dict, Any, Optional
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


class VisualizerAndSynthesizer:
    """Responsible for deriving analytical insights and visualizing data."""

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing.")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def synthesize_insights(self, user_query: str, data: List[Dict[str, Any]]) -> str:
        """Translating numerical outputs into concise analytical conclusions and recommendations for decision-makers."""
        if not data:
            return "لم يتم العثور على سجلات تطابق شروط الاستعلام المطلوبة."

        # Converting the data sample into a prompt
        df_sample = pd.DataFrame(data).head(10).to_markdown(index=False)

        prompt = f"""
            You are an Executive Senior Data Analyst.
            Translate the following query results into a concise, professional executive briefing.

            User Question: {user_query}

            Extracted Data:
            {df_sample}

            Rules:
            1. Provide a direct answer in 1-2 sharp sentences.
            2. Highlight 2-3 key quantitative findings (use bullet points with percentages, ranks, or totals).
            3. Conclude with one actionable business recommendation.
            4. Respond in the same language as the user's question (Arabic if Arabic, English if English).
            """

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return response.text.strip()

    def create_figure(
        self, data: List[Dict[str, Any]], chart_type: str = "bar"
    ) -> Optional[go.Figure]:
        """Create an interactive chart object using Plotly based on the column structure."""
        if not data:
            return None

        df = pd.DataFrame(data)
        if len(df.columns) < 2:
            return None

        # Automatic column sorting: Categorical/Date and Numeric.
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        non_numeric_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

        if not numeric_cols:
            return None

        x_col = non_numeric_cols[0] if non_numeric_cols else df.columns[0]
        y_col = numeric_cols[0]

        # Selecting a modern design style for facades
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
    gen = SQLGenerator()
    executor = SafeSQLExecutor(db_mgr, gen)
    viz = VisualizerAndSynthesizer()

    query = "ما هي إيرادات كل منطقة جغرافية بعد الخصم؟"
    exec_res = executor.run_with_self_healing(query, schema)

    if exec_res.success:
        print("--- Data Table ---")
        print(pd.DataFrame(exec_res.data))

        print("\n--- Executive Summary (LLM Insights) ---")
        insights = viz.synthesize_insights(query, exec_res.data)
        print(insights)

        fig = viz.create_figure(exec_res.data, chart_type=exec_res.intended_chart_type)
        if fig:
            print("\n Plotly Figure generated successfully.")