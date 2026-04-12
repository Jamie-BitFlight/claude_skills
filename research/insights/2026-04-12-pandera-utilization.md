# Utilization Proposals: Pandera

**Research entry**: ./research/data-infrastructure/pandera.md
**Generated**: 2026-04-12
**Integration surfaces found**: 2 (pip dependency, decorator API)
**Proposals written**: 1
**Skipped**: 2 — no data-processing scope, out-of-scope CLI tools

---

## Utilization 1: python-pytest-architect → Pandera

**Research entry**: ./research/data-infrastructure/pandera.md
**Caller**: plugins/python-engineering/agents/python-pytest-architect.md
**Integration mechanism**: pip dependency
**Replaces or adds**: Adds: property-based testing of data processing code via Pandera schema-driven synthetic data generation
**Setup cost**: Low (pip install only; no auth or config required)
**Integration surface**: `pip install pandera[hypothesis]` package, `@given(MySchema.strategy(size=N))` decorator

### Why this caller

The python-pytest-architect agent (lines 3, 22, 40-42 of its agent file) explicitly lists "hypothesis property-based tests" as a core competency and mentions "Hypothesis Integration" as a key feature in its quality checklist ("mutation testing plan"). The research entry documents Pandera's hypothesis integration feature (lines 91-94): "Pandera integrates with hypothesis for property-based testing and automatic synthetic data generation." Currently, property-based tests using hypothesis would require developers to hand-craft test data strategies or use generic hypothesis `@st` strategies. Pandera eliminates this friction by enabling test authors to define a schema once (using Pandera's class-based API with type hints matching their Pydantic models) and automatically generate diverse valid test data via `MySchema.strategy(size=N)`. This closes the gap between hypothesis adoption intent and practical test data generation — letting python-pytest-architect create high-quality property-based tests without the boilerplate of custom strategy functions.

### Integration sketch

```python
# Before (manual hypothesis strategy)
from hypothesis import given, strategies as st

@given(st.lists(st.dictionaries({
    'customer_id': st.integers(min_value=1),
    'purchase_amount': st.floats(min_value=0.01, max_value=10000),
    'purchase_date': st.dates(min_value=date(2020, 1, 1))
}), min_size=1, max_size=100))
def test_transaction_processing(transactions_list):
    df = pd.DataFrame(transactions_list)
    result = process_transactions(df)
    assert result.shape[0] > 0

# After (Pandera schema-driven)
import pandera as pa
from pandera.typing import Series
from hypothesis import given

class TransactionSchema(pa.DataFrameModel):
    customer_id: int = pa.Field(gt=0)
    purchase_amount: float = pa.Field(gt=0.01, lt=10000)
    purchase_date: str = pa.Field()  # or datetime with constraints

    class Config:
        strict = True

@given(TransactionSchema.strategy(size=10))
def test_transaction_processing(df):
    validated_df = TransactionSchema.validate(df)
    result = process_transactions(validated_df)
    assert result.shape[0] > 0
```

The schema serves dual purposes: (1) defines validation constraints that hypothesis respects during data generation, (2) validates actual test data at assertion time. Both are grounded in the same declarative definition, eliminating strategy/validator drift.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| plugins/python-engineering/agents/python-cli-architect.md | CLI architecture scope; Pandera is for DataFrame validation, not CLI I/O streams. The research entry's FastAPI integration (lines 113-118) is a data-API pattern, not CLI-tool pattern. No overlap with python-cli-architect's Typer/Rich focus. |
| plugins/development-harness/agents/t0-baseline-capture.md | Captures baseline via bash command exit codes, stdout, stderr (line 54-65 of agent file). Pandera validates pandas/polars/PySpark DataFrames, not bash command outputs. No integration surface match. |
