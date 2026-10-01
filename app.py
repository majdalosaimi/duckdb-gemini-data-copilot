"""
app.py
An interactive application for conversing with and analyzing data using Streamlit, DuckDB, and the Gemini API.
"""

import streamlit as st
import pandas as pd
from src.database import DatabaseManager
from src.generator import SQLGenerator
from src.executor import SafeSQLExecutor
from src.visualizer import VisualizerAndSynthesizer

# Adjust page settings
st.set_page_config(
    page_title="AI Data Copilot | DuckDB & Gemini",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Configuring services and the data engine using resource caching.
@st.cache_resource
def get_services():
    db_mgr = DatabaseManager(db_path="data/analytics.duckdb", read_only=True)
    generator = SQLGenerator(primary_model="gemini-3.8-flash")
    executor = SafeSQLExecutor(db_manager=db_mgr, generator=generator, max_retries=2)
    visualizer = VisualizerAndSynthesizer(primary_model="gemini-3.8-flash")
    schema_context = db_mgr.get_schema_context()
    return db_mgr, executor, visualizer, schema_context


db_mgr, executor, visualizer, schema_context = get_services()

# Conversation state management
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Sidebar ---
with st.sidebar:
    st.title("🗄️ Database Context")
    st.caption("Active Engine: DuckDB (Read-Only)")
    
    with st.expander("Explore Database Schema", expanded=False):
        st.code(schema_context, language="yaml")
        
    st.divider()
    st.markdown("### 💡 أسئلة استكشافية مقترحة:")
    sample_queries = [
        "ما هي أعلى 3 منتجات مبيعاً من حيث الإيرادات بعد الخصم؟",
        "احسب إجمالي الإيرادات لكل منطقة جغرافية",
        "ما هي أكثر القطاعات إنفاقاً على الخدمات والبرمجيات؟",
        "أظهر تفاصيل المبيعات الشهرية مع عدد الطلبات"
    ]
    for q in sample_queries:
        if st.button(q, use_container_width=True):
            st.session_state.preset_query = q

    if st.button("🗑️ مسح المحادثة", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- Main Chat Interface ---
st.title("📊 AI Data Analyst Copilot")
st.markdown(
    "اطرح أسئلتك بلغة طبيعية للحصول على استعلامات SQL، تحليلات تنفيذية، ورسوم بيانية فورية."
)

# Show previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # If there is data recorded in the message
        if "sql" in msg:
            with st.expander("🔍 تفاصيل الاستعلام (Generated SQL)"):
                st.code(msg["sql"], language="sql")
                if msg.get("explanation"):
                    st.caption(msg["explanation"])
                    
        if "df" in msg and msg["df"] is not None:
            st.dataframe(msg["df"], use_container_width=True)
            
        if "fig" in msg and msg["fig"] is not None:
            st.plotly_chart(msg["fig"], use_container_width=True)

# Receiving the new question
preset_input = st.session_state.pop("preset_query", None)
user_prompt = st.chat_input("اكتب سؤالك التحليلي هنا...") or preset_input

if user_prompt:
    # 1. Display user question
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # 2. Processing and generating the result
    with st.chat_message("assistant"):
        with st.spinner("جاري تحليل السؤال وكتابة استعلام SQL والتحقق الأمني..."):
            exec_result = executor.run_with_self_healing(
                user_query=user_prompt,
                schema_context=schema_context
            )

        if not exec_result.success:
            error_text = f"❌ تعذر تنفيذ الاستعلام:\n```text\n{exec_result.error_message}\n```"
            st.markdown(error_text)
            st.session_state.messages.append({"role": "assistant", "content": error_text})
        else:
            df = pd.DataFrame(exec_result.data)
            
            # Formulating the conclusion and the graph
            with st.spinner("جاري استخلاص النتائج التنفيذية وبناء المخطط البياني..."):
                insights = visualizer.synthesize_insights(user_prompt, exec_result.data)
                fig = visualizer.create_figure(exec_result.data, chart_type=exec_result.intended_chart_type)

            # View the executive report
            st.markdown(insights)

            # Display the query executed within the Expander.
            with st.expander("🔍 تفاصيل الاستعلام (Generated SQL)"):
                st.code(exec_result.sql_query, language="sql")
                if exec_result.explanation:
                    st.caption(f"**الشرح المنطقي:** {exec_result.explanation}")
                if exec_result.retries_used > 0:
                    st.info(f"تم تفعيل حلقة التصحيح الذاتي ({exec_result.retries_used}) مرات للوصول للصيغة الصحيحة.")

            # Show table
            st.dataframe(df, use_container_width=True)

            # Display the chart, if available.
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            # Save the message and its data to the session.
            st.session_state.messages.append({
                "role": "assistant",
                "content": insights,
                "sql": exec_result.sql_query,
                "explanation": exec_result.explanation,
                "df": df,
                "fig": fig
            })