# Utilization Proposals: PageIndex

**Research entry**: ./research/context-management/pageindex.md
**Generated**: 2026-10-02
**Integration surfaces found**: 2 (SDK | integration framework)
**Proposals written**: 2
**Skipped**: 1

Scope of both proposals: PDF source documents only. In local mode the PageIndex SDK's
`submit_document` rejects any file whose name does not end in `.pdf` (`pageindex/local_api.py`,
class `LocalAPI`: "only PDF files are supported in local mode"; recorded in the entry under
Limitations and Technical Architecture > Indexing Flow). The research entries in `./research/` are
Markdown, so neither proposal applies to them. Markdown navigation is already served by the
`progressive_markdown` engine (`plugins/development-harness/docs/agent-markdown-consumption-contract.md`,
R1). No failure of either caller on a long PDF has been observed; see
`./research/insights/2026-10-02-pageindex-improvements.md` (Improvement 1, "Deferred"). Both
proposals are therefore conditional: they describe the integration surface if an assessment ever
needs to read a PDF, and are not a claim that a gap exists today.

---

## Utilization 1: research-utilization-assessor → PageIndex SDK (PDF sources only)

**Research entry**: ./research/context-management/pageindex.md
**Caller**: ./.claude/agents/research-utilization-assessor.md
**Integration mechanism**: pip dependency (Python SDK) + API calls
**Replaces or adds**: Adds the ability to query a long PDF source document (for example a vendor manual or paper cited by a research entry) by section instead of reading it whole. No change for Markdown entries.
**Setup cost**: Low for the call itself (`pip install -U pageindex` plus an LLM API key); the dependency decision belongs to the agent's owner
**Integration surface**: `PageIndexClient` class, `submit_document(file_path)` (PDF only in local mode), `chat(question, doc_id=doc_id)`

### Why this caller

`research-utilization-assessor` takes one Markdown research entry and decides whether a local
system could call or depend on the described tool. It reads the entry directly, and the entry is
short Markdown (`research/context-management/pageindex.md` is 247 lines), so PageIndex adds nothing
for that input. The case for PageIndex exists only when the assessment must consult a PDF that the
entry cites, such as a specification too long to read in full. The upstream README reports that for
PDFs, native PDF input costs 2.1x more than tree retrieval at 52 pages and 16.6x more at 420 pages
(`gpt-5.6-sol`, prompt caching excluded; entry, Key Features > Cost Efficiency). That figure
compares native PDF input to tree retrieval on those PDFs. It says nothing about Markdown entries
of this repository's size, and no PDF-reading step has been observed in this agent's runs, so it is
cited here only as the upstream measurement that would justify the work if such a PDF appears.

### Integration sketch

```python
from pageindex import PageIndexClient
import os

os.environ["OPENAI_API_KEY"] = "your-key"

client = PageIndexClient(
    index="gpt-5.6-luna",  # model that builds/refines the tree index
    chat="gpt-5.6-sol",  # model that searches the tree
)

# Only a PDF source document is a supported input to local-mode submit_document.
pdf_path = "./path/to/cited-source.pdf"
doc_id = client.submit_document(pdf_path)["doc_id"]

# Ask about one capability; only the tree nodes the model reaches are read.
integration_surface = client.chat("What command-line flags or API endpoints does this document define?", doc_id=doc_id)
print(integration_surface)
```

---

## Utilization 2: research-insight-extractor → PageIndex SDK (PDF sources only)

**Research entry**: ./research/context-management/pageindex.md
**Caller**: ./.claude/agents/research-insight-extractor.md
**Integration mechanism**: pip dependency (Python SDK) + API calls
**Replaces or adds**: Adds the ability to query several PDF source documents in one `chat` call when an extraction must compare a cited PDF against others. No change for Markdown entries.
**Setup cost**: Low for the call itself (`pip install -U pageindex` plus an LLM API key); the dependency decision belongs to the agent's owner
**Integration surface**: `PageIndexClient` class, `submit_document(file_path)` (PDF only in local mode), `chat(question, doc_id=[...])` (`doc_id` is typed `Optional[Union[str, list[str]]]` in `pageindex/client.py`, recorded in the entry under Technical Architecture > Retrieval Flow)

### Why this caller

`research-insight-extractor` reads one research entry per run, maps its patterns to local systems,
and writes improvement proposals (`.claude/agents/research-insight-extractor.md`, "Takes one
completed research entry and produces concrete, measurable improvement proposals ..."). The input
is Markdown that the agent reads and compares directly, so PageIndex does not apply to it. Whether
any cross-document relationships are modeled when several documents are queried is not mentioned
in the upstream documentation (entry, Limitations > Multi-document reasoning), so this proposal
claims only that a list of PDF `doc_id` values can be passed to `chat`, not that cross-document
patterns will be found. It applies only if an extraction has to read two or more cited PDFs, which
has not been observed.

### Integration sketch

```python
from pageindex import PageIndexClient
import os

os.environ["OPENAI_API_KEY"] = "your-key"

client = PageIndexClient(index="gpt-5.6-luna", chat="gpt-5.6-sol")

# PDF sources cited by research entries; Markdown paths are rejected in local mode.
pdf_paths = ["./path/to/source-a.pdf", "./path/to/source-b.pdf"]
doc_ids = [client.submit_document(path)["doc_id"] for path in pdf_paths]

# `doc_id` accepts a list of IDs (pageindex/client.py, PageIndexClient.chat signature).
answer = client.chat("Which sections of these documents describe retry or caching behavior?", doc_id=doc_ids)
print(answer)
```

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| Markdown research entries as PageIndex input (both callers) | `submit_document` in local mode accepts only `.pdf` files, and no Markdown-to-PDF conversion stage is documented upstream; `progressive_markdown` already provides section-level navigation for Markdown (contract R1). Not presented as an integration. |
