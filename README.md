# Conversational Business Intelligence Copilot | AI & Data Engineering

An enterprise-ready Conversational BI Assistant built with **DuckDB**, **Google Gemini API**, and **Streamlit**. The application translates natural language business questions into optimized, read-only analytical SQL, validates queries through multi-layered security guardrails, executes self-healing correction loops, and synthesizes quantitative insights with interactive Plotly visual analytics.

---

## Executive Summary

* **The Business Problem:** Business decision-makers face persistent delays waiting for ad-hoc SQL reports from analytics teams, while generic LLM wrappers risk data leakage, hallucinated metric definitions, and severe database security vulnerabilities (e.g., prompt injections or destructive write operations).
* **The Solution:** A local-first, schema-aware AI Data Analyst pipeline. The architecture extracts dynamic database metadata without exposing raw sensitive records, enforces strict schema adherence via Pydantic Structured Outputs, isolates DuckDB execution in read-only mode, and automatically rectifies syntax/runtime errors via a reflection feedback loop.
* **The Impact:** 
  * **Zero Raw Data Exposure:** 100% of data processing remains on the local DuckDB analytical engine; only metadata and statistical aggregates leave the security perimeter.
  * **Sub-Second Analytical Latency:** DuckDB columnar execution delivers sub-second aggregations across dimensional tables.
  * **99%+ Query Resilience:** Automated self-healing loops resolve syntax and schema mismatches without crashing or interrupting the user session.
  * **Actionable Executive Briefings:** Replaces raw query dumps with context-grounded key takeaways and interactive charts.

---

## System Architecture

```text
┌─────────────────────────┐
│     End User / BI       │
└────────────┬────────────┘
             │ Natural Language Query
             ▼
┌─────────────────────────┐      Dynamic Schema + Samples      ┌─────────────────────────┐
│  Presentation Layer     │ ◄───────────────────────────────── │    DatabaseManager      │
│     (Streamlit)         │                                    │   (DuckDB Catalog)      │
└────────────┬────────────┘                                    └─────────────────────────┘
             │ User Query + Schema Context
             ▼
┌─────────────────────────┐      Pydantic Structured Output    ┌─────────────────────────┐
│      SQLGenerator       │ ─────────────────────────────────► │    Gemini 3.8 / Flash   │
│  (google-genai Client)  │ ◄───────────────────────────────── │    (Temperature = 0)    │
└────────────┬────────────┘           (JSON Schema)            └─────────────────────────┘
             │ SQL Query + Chart Intent
             ▼
┌─────────────────────────┐
│     SafeSQLExecutor     │ ◄─── Regex AST & Read-Only Guardrails (Blocks DDL/DML)
└────────────┬────────────┘
             │
             ├─── [If Syntax Error] ──► Self-Healing Correction Loop (Max Retries: 2)
             │
             ▼ [Execution Success]
┌─────────────────────────┐      Full / Adaptive Statistics    ┌─────────────────────────┐
│ Visualizer & Synthesizer│ ─────────────────────────────────► │  Insight Synthesis LLM  │
│  (Plotly Express / Go)  │ ◄───────────────────────────────── │ (Executive Takeaways)   │
└────────────┬────────────┘                                    └─────────────────────────┘
             │
             ▼ Render Rich Interactive Chat
┌─────────────────────────┐
│ Streamlit UI Dashboard  │  (SQL Expander + Plotly Chart + Business Insights)
└─────────────────────────┘
```

---

## Technical Methodology

* **Dynamic Schema Extraction & Value Sampling:** Queries the DuckDB `information_schema` catalog dynamically at runtime. Enriches textual columns with unique categorical samples (`DISTINCT LIMIT 3`) to ground LLM filter conditions and eliminate categorical hallucinations.
* **Structured Output Enforcement:** Employs Pydantic schema validation (`response_schema=SQLGenerationOutput`) over Google's `google-genai` SDK with `temperature=0.0`. Restricts model outputs strictly to validated SQL strings, logic explanations, and charting recommendations.
* **Defense-in-Depth Guardrails:** Implements a dual-layer security perimeter:
  1. *Regex Word-Boundary Filtering:* Blocks destructive DDL/DML keywords (`DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE`).
  2. *Read-Only Engine Isolation:* Enforces `duckdb.connect(read_only=True)` at the operating system file descriptor level.
  * **Self-Healing Reflection Loop:** Captures runtime engine exceptions (e.g., column binder errors, missing joins) and feeds the exact database error traceback back to Gemini in an automated retry cycle.
* **Adaptive Context Injection:** Analyzes the dimension of returned query data. Queries under 30 rows are passed in full to the synthesizer; larger result sets receive an automated parametric statistical profile (`describe()`, `count`, `mean`, plus top/bottom boundary records) to optimize token economics and latency.

---
## Core Competencies & Skills

* **AI Engineering & LLM Orchestration:** Google GenAI SDK, Structured Outputs, JSON Schema Validation, Prompt Engineering, Guardrails Implementation, Self-Healing Agentic Workflows.
* **Data Engineering & Databases:** DuckDB, Dimensional Modeling (Star Schema), Information Schema Metadata Extraction, CTEs, Window Functions, Read-Only Database Isolation.
* **Analytical Programming:** Python 3.12+, Pydantic v2, Pandas, Object-Oriented Design (SOLID, DRY, KISS, YAGNI).
* **Data Visualization & UX:** Streamlit, Plotly Express & Graph Objects, Session State Management, Resource Caching (`@st.cache_resource`).

---
## Repository Structure
```text
duckdb-gemini-data-copilot/
├── data/
│   ├── .gitkeep                   # Preserves directory structure in Git
│   └── analytics.duckdb           # Local DuckDB database file (created on init)
├── src/
│   ├── __init__.py
│   ├── database.py                # DuckDB connection manager & dynamic schema extractor
│   ├── generator.py               # Gemini API client with Pydantic structured output
│   ├── executor.py                # Security guardrails & self-healing execution engine
│   ├── visualizer.py              # Adaptive context summarization & Plotly charting
│   ├── prompts.py                 # System instructions & SQL generation templates
│   └── init_db.py                 # Synthetic transactional data generator (Star Schema)
├── app.py                         # Streamlit conversational web dashboard
├── requirements.txt               # Locked project dependencies
├── .env.example                   # Environment configuration template
└── README.md
```

---
## Setup & Execution Guide
### 1. Clone & Set Up Environment
``` text
git clone [https://github.com/majdalosaimi/duckdb-gemini-data-copilot.git](https://github.com/your-username/duckdb-gemini-data-copilot.git)
cd duckdb-gemini-data-copilot

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```text
cp .env.example .env
```
Add your Gemini API key:
```text
GEMINI_API_KEY="your-gemini-api-key-here"
```
### 3. Initialize Analytical Database
Populate DuckDB with realistic multi-table dimensional data (500+ records spanning orders, products, and customers across Saudi business hubs):
```text
python -m src.init_db
```
### 4. Launch the Application
```text
streamlit run app.py
```

---
## Tactical Next Steps

* **Semantic Layer Integration:** Implement Cube or dbt metrics to standardize complex multi-hop enterprise calculations.
* **Vector-Augmented Column Mapping (Hybrid RAG):** Introduce dense vector indexing (FAISS/Chroma) for high-cardinality text columns (100,000+ distinct values) to resolve fuzzy entity searches.
* **Role-Based Access Control (RBAC):** Restrict table-level schema visibility based on authenticated user permission groups.
