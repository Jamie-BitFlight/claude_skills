# Utilization Proposals: Magnitude

**Research entry**: ./research/llm-infrastructure/magnitude.md
**Generated**: 2026-10-03
**Integration surfaces found**: 2 (API | CLI)
**Proposals written**: 2
**Skipped**: 2 — no local caller found by search; litellm embeddings path has no documented Magnitude endpoint

---

## Utilization 1: plugins/litellm/skills/litellm/SKILL.md → Magnitude OpenAI-compatible endpoint

**Research entry**: ./research/llm-infrastructure/magnitude.md
**Caller**: plugins/litellm/skills/litellm/SKILL.md
**Integration mechanism**: API call
**Replaces or adds**: Adds a second documented local backend to the skill's "Llamafile Integration" section, which today hard-codes `http://localhost:8080/v1` as the only local `api_base`. The skill's line 30 lists "llamafile, Ollama, LocalAI, vLLM" with no recipe for any but llamafile.
**Setup cost**: Medium (desktop app install, hardware assessment, model pull; no API key documented)
**Integration surface**: `http://127.0.0.1:10100/inference/v1/chat/completions` (also `/inference/v1/models`, `/health`); Anthropic format at `http://127.0.0.1:10100/inference/anthropic/v1/messages`

### Why this caller

`plugins/litellm/skills/litellm/SKILL.md` (read in full sections: lines 1-70 and 276-330) teaches the `llamafile/` model prefix with `api_base = "http://localhost:8080/v1"`, a proxy `config.yaml` entry, and `verify_llamafile_connection()`. All local-server guidance is llamafile-specific. Magnitude serves the same OpenAI chat-completions contract on a different port and path prefix (`/inference/v1`), so a user routing LiteLLM to Magnitude hits the exact class of mistake the skill already warns about (wrong port, wrong `/v1` suffix). Adding a short section closes that gap.

Search evidence: `grep -rIl -i "magnitude" plugins/llamafile plugins/litellm` returned no matches (rc=1), so neither plugin mentions Magnitude today.

### Integration sketch

Grounded in the research entry's documented base URL and chat-completions endpoint. The research entry does not document a LiteLLM provider prefix for Magnitude; the model-prefix choice (`llamafile/` as the skill already uses for a generic OpenAI-compatible server, versus another prefix) is deferred and must be verified against LiteLLM docs before the skill is edited. `MODEL_ID` comes from `magnitude catalog list` / `GET /inference/v1/models`.

```python
import litellm

response = litellm.completion(
    model="<prefix-TBD>/MODEL_ID",
    messages=[{"role": "user", "content": "Explain inference optimization."}],
    api_base="http://127.0.0.1:10100/inference/v1",
    max_tokens=256,
)
```

Health probe for `verify_*_connection`: `GET http://127.0.0.1:10100/health`. Note the entry documents first-response latency after idle (on-demand model load), so connection checks should use a generous timeout.

---

## Utilization 2: plugins/llamafile/skills/llamafile/SKILL.md → magnitude CLI (alternative engine)

**Research entry**: ./research/llm-infrastructure/magnitude.md
**Caller**: plugins/llamafile/skills/llamafile/SKILL.md
**Integration mechanism**: CLI subprocess
**Replaces or adds**: Adds an alternative local engine for the skill's "Server Management" / "Process Management Script" pattern (lines ~247-300), where users who want GPU acceleration currently tune `--n-gpu-layers` by hand (line 144). Magnitude's entry documents on-device kernel tuning and a hardware-matched model recommender (`Discover`), reported by the vendor as up to 2x faster than llama.cpp (the "up to 2x" figure has no measurement method in the README or docs; the 92% Metal decode figure was measured on a Mac M4 Pro 48 GB with Qwen 3.6 35B A3B, 4-bit, 64k context, no speculative decoding, per the README benchmark graphic; research entry snapshot, accessed 2026-10-02; llamafile builds on llama.cpp per SKILL.md line 29).
**Setup cost**: Medium (desktop app download; CLI ships with it)
**Integration surface**: `magnitude serve`, `magnitude catalog pull <model-id>`, `magnitude models load <model-id>`, `magnitude status`, `magnitude hardware`

### Why this caller

`plugins/llamafile/skills/llamafile/SKILL.md` (read lines 1-50, 100-165, 247-330, and grep for alternatives) defines server start, GPU flags, and a Python process-management helper that shells out to the llamafile binary. It names llama.cpp only as the underlying engine (lines 443, 464). Magnitude exposes an equivalent lifecycle through a CLI, so the helper pattern can be mirrored with a different command and port. Scope caution: the speed claim is vendor-reported against llama.cpp, not llamafile, and is unverified locally; propose as an alternative path, not a replacement.

Search evidence: the same `grep -rIl -i "magnitude"` over `plugins/llamafile` returned no matches.

### Integration sketch

Commands are taken verbatim from the research entry's CLI Reference. The helper mirrors the skill's subprocess pattern; no flags beyond those documented are used.

```python
import subprocess

subprocess.run(["magnitude", "catalog", "pull", model_id], check=True)
subprocess.run(["magnitude", "models", "load", model_id], check=True)
server = subprocess.Popen(["magnitude", "serve"])  # foreground service, no Desktop
# readiness: GET http://127.0.0.1:10100/health ; state: `magnitude status`
```

Documented limits to carry into the skill: API is inference-only (no model download or management over HTTP, so pulls must use the CLI), and dedicated-GPU machines are bounded by VRAM, not system RAM.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| plugins/litellm/skills/litellm/SKILL.md embeddings section (line ~158, `embedding(model="llamafile/...")`) | Research entry documents no `/embeddings` endpoint for Magnitude (endpoints listed: chat/completions, completions, responses, models, health, anthropic messages and count_tokens); not proposed. |
| Agents, hooks, and workflow scripts under `.claude/` and `plugins/*/` | Search `grep -rIl -E "127\.0\.0\.1:8080\|localhost:8080\|llamafile\|ollama\|ANTHROPIC_BASE_URL" plugins .claude scripts` returned only llamafile and litellm plugin files, a robotframework reference, fastmcp auth reference, and two unrelated `.claude/skills` docs; no other local caller of a local inference server found. |
