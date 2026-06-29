---
title: "AI Data Science Team"
research_date: "2026-03-04"
source_url: "https://github.com/business-science/ai-data-science-team"
github_url: "https://github.com/business-science/ai-data-science-team"
version_at_research: "0.0.0.9017"
license: "MIT"
last_verified: "2026-03-04"
version_at_verification: "0.0.0.9017"
next_review: "2026-06-04"
---

## Overview

AI Data Science Team is a Python library of specialized LangGraph/LangChain agents that automate common data science tasks (data loading, cleaning, wrangling, visualization, feature engineering, SQL querying, and ML modeling). Agents can be composed into supervisor-led multi-agent workflows that route tasks across the team end-to-end. The repository also ships **AI Pipeline Studio**, a Streamlit application that wraps the agent library into a visual, pipeline-first workspace with lineage tracking and reproducible script export.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Data science tasks require switching between many tools and writing repetitive boilerplate code | Specialized agents handle each task domain (cleaning, wrangling, EDA, ML) and generate executable Python code |
| Multi-step data science pipelines are hard to orchestrate and reproduce | Supervisor Agent routes tasks across specialized agents; AI Pipeline Studio records each step with lineage tracking |
| LLM-generated code may execute unsafe operations | Sandboxed subprocess execution with blocked dangerous imports, disabled network access, and configurable timeouts and memory limits |
| Local LLM deployment requires complex integration | LangChain abstraction layer supports both OpenAI-compatible APIs and Ollama local models via a single `llm=` parameter |
| Data scientists need reproducible, auditable workflows | Pipeline Studio exports reproducible Python scripts per step; project state saves as metadata-only or full-data bundles |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 5,011 | 2026-03-04 |
| GitHub Forks | 863 | 2026-03-04 |
| Contributors | 2 (from paginated header, page 2 is last) | 2026-03-04 |
| Open Issues | 28 | 2026-03-04 |
| Latest Release | 0.0.0.9017 | 2025-12-20 |
| Repository Created | 2024-12-11 | 2026-03-04 |
| PyPI Downloads/month | Not published (install from source or PyPI) | 2026-03-04 |
| Python Support | 3.9, 3.10, 3.11, 3.12, 3.13 | 2026-03-04 |

---

## Key Features

### Specialized Agent Library

- **Data Loader Tools Agent**: file ingestion with conversational interface and multi-format support
- **Data Wrangling Agent**: pandas-based transformations driven by natural-language instructions
- **Data Cleaning Agent**: automated detection and remediation of missing values, duplicates, type errors
- **Data Visualization Agent**: generates Plotly charts from natural-language chart requests
- **EDA Tools Agent**: exploratory data analysis with automated reports (sweetviz, missingno)
- **Feature Engineering Agent**: creates and transforms features from natural-language specifications
- **SQL Database Agent**: SQLAlchemy-backed natural-language SQL query generation and execution
- **H2O ML Agent**: AutoML model training with H2O, produces holdout evaluation metrics, ROC curves, confusion matrices, residual plots
- **MLflow Tools Agent**: experiment tracking and model registry interaction
- **Workflow Planner Agent**: generates structured, ordered workflow plans with prerequisites and clarifying questions

### Multi-Agent Orchestration

- **Supervisor Agent**: LangGraph supervisor that routes user requests to the appropriate specialist agent and aggregates results
- **Pandas Data Analyst**: pre-built multi-agent workflow combining loader, wrangling, and visualization agents
- **SQL Data Analyst**: pre-built multi-agent workflow combining SQL agent with visualization and EDA
- Message-first API throughout (LangChain 1.0+ compatible); all agents expose conversational interfaces

### AI Pipeline Studio (Flagship App)

- Visual pipeline editor with step lineage tracking
- Views: Table, Chart, EDA, Code, Model, Predictions, MLflow
- Manual pipeline steps interleaved with AI agent steps
- Multi-dataset handling and merge workflows
- Project save/load in metadata-only or full-data modes
- Storage footprint controls and rehydrate workflows
- Run with: `streamlit run apps/ai-pipeline-studio-app/app.py`

### Safety and Security

- Sandboxed subprocess execution for all LLM-generated code
- Blocked dangerous imports inside sandbox
- Network access disabled within sandbox
- Configurable execution timeouts and memory limits
- Fixed vulnerability in `load_pickle` operations (release 0.0.0.9017)

---

## Technical Architecture

The library is structured as three layers:

**Layer 1 — Tools** (`ai_data_science_team/tools/`): low-level Python functions wrapping pandas, SQLAlchemy, Plotly, H2O, MLflow, and scikit-learn operations. Tools are injected into agents as callable LangChain tools.

**Layer 2 — Agents** (`ai_data_science_team/agents/`, `ds_agents/`, `ml_agents/`): individual LangGraph `StateGraph` agents. Each agent has its own state schema, system prompt, tool list, and message-first interface. Agents are composable building blocks.

**Layer 3 — Multi-Agents** (`ai_data_science_team/multiagents/`): supervisor-pattern orchestration built on LangGraph. The `orchestration.py` module provides the routing logic. The Supervisor Agent receives user requests, determines which specialist agent to invoke, passes context, and aggregates results.

**App Layer** (`apps/`): Streamlit applications consuming the library. AI Pipeline Studio (`apps/ai-pipeline-studio-app/`) wraps the multi-agent layer with a visual editor and pipeline state manager.

**LLM Backend**: Any LangChain-compatible chat model. The `llm=` parameter accepts `ChatOpenAI`, `ChatOllama`, or any `BaseChatModel`. Agents do not hard-code any specific model.

**Code Execution**: LangChain Experimental's `PythonAstREPLTool` is used for code execution within a sandboxed subprocess (as of 0.0.0.9017).

---

## Installation & Usage

```bash
# Install from PyPI
pip install ai-data-science-team

# Install with ML extras (H2O + MLflow)
pip install "ai-data-science-team[machine-learning]"

# Install with data science EDA extras (pytimetk, missingno, sweetviz)
pip install "ai-data-science-team[data-science]"

# Install all extras
pip install "ai-data-science-team[all]"

# Or install from source in editable mode
git clone https://github.com/business-science/ai-data-science-team.git
cd ai-data-science-team
pip install -e .

# Run AI Pipeline Studio
streamlit run apps/ai-pipeline-studio-app/app.py
```

```python
from langchain_openai import ChatOpenAI
from ai_data_science_team.agents.data_wrangling_agent import DataWranglingAgent
import pandas as pd

llm = ChatOpenAI(model_name="gpt-4o-mini")

df = pd.read_csv("data/sales.csv")

agent = DataWranglingAgent(
    model=llm,
    n_samples=50,
    log=True,
    log_path="logs/",
)

result = agent.invoke_agent(
    user_instructions="Group by region and calculate total revenue per region",
    data_raw=df,
)

df_wrangled = agent.get_data_wrangled()
code = agent.get_data_wrangling_function()  # retrieve the generated Python function
```

```python
# Local LLM via Ollama
from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.1:8b")
# Use same agent interface — llm= parameter accepts any LangChain BaseChatModel
```

```python
# Supervisor-led multi-agent workflow
from ai_data_science_team.multiagents import DataScienceTeam

team = DataScienceTeam(model=llm)
response = team.invoke({"messages": [{"role": "user", "content": "Load data.csv, clean it, and show a correlation heatmap"}]})
```

---

## Relevance to Claude Code Development

### Applications

- **Pattern reference for domain-specific agent teams**: the library demonstrates how to decompose a complex domain (data science) into specialist agents with clear task boundaries and compose them under a supervisor. This pattern is directly applicable to building Claude Code skill-agents with domain specialization.
- **Sandboxed code execution model**: the sandboxed subprocess approach for LLM-generated code is a production-grade safety pattern worth studying for any agent that generates and executes code.
- **Message-first API design**: all agents expose consistent `invoke_agent()` interfaces and state retrieval methods (`get_data_wrangled()`, `get_data_wrangling_function()`), which is a clean pattern for agent output contracts.

### Patterns Worth Adopting

- **Explicit output retrieval methods**: agents expose typed getter methods for their outputs (code, data, plots) rather than parsing unstructured text — eliminates downstream parsing fragility.
- **Log + log_path parameters on every agent**: every agent accepts `log=True` and `log_path=` for audit trails. This is a simple but high-value observability pattern for debugging agent pipelines.
- **n_samples parameter for context efficiency**: agents accept a `n_samples` parameter to limit dataframe rows sent to the LLM context window — a concrete approach to context budget management.
- **Extras-based optional dependencies**: `[machine-learning]`, `[data-science]`, `[all]` extras prevent heavy dependencies (H2O, MLflow) from being required for basic usage.

### Integration Opportunities

- **Claude Code data science skill**: the agent patterns here could inform a Claude Code skill for data science workflows, where Claude orchestrates these agents as tools.
- **Reference implementation for multi-agent patterns research**: the supervisor + specialist architecture is one of the cleaner open-source implementations of this pattern built on LangGraph 1.0+.
- **MCP tool wrapping**: individual agents (especially SQL Database Agent and Data Wrangling Agent) could be exposed as MCP tools, making them callable from Claude Code without requiring the full library.

---

## References

- [GitHub Repository: business-science/ai-data-science-team](https://github.com/business-science/ai-data-science-team) (accessed 2026-03-04)
- [PyPI: ai-data-science-team](https://pypi.org/project/ai-data-science-team/) (accessed 2026-03-04)
- [Release 0.0.0.9017 notes](https://github.com/business-science/ai-data-science-team/releases/tag/0.0.0.9017) (accessed 2026-03-04)
- [GitHub API: repos/business-science/ai-data-science-team](https://api.github.com/repos/business-science/ai-data-science-team) (accessed 2026-03-04)

---
