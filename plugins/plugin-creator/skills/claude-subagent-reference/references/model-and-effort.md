# Model and Effort Configuration

SOURCE: <https://code.claude.com/docs/en/model-config.md> (accessed 2026-05-28)
SOURCE: <https://code.claude.com/docs/en/sub-agents#choose-a-model> (accessed 2026-09-24)

## Model field

The `model` frontmatter field accepts:

| Value | Behavior |
|:------|:---------|
| `sonnet` | Latest Sonnet model — daily coding tasks. On Anthropic API: Sonnet 4.6. On Bedrock/Vertex: Sonnet 4.5 |
| `opus` | Latest Opus model — complex reasoning. On Anthropic API: Opus 4.7. On Bedrock/Vertex: Opus 4.6 |
| `haiku` | Fast, efficient model for simple tasks |
| `fable` | Current Fable model alias |
| Full model ID | e.g., `claude-opus-4-7`, `claude-sonnet-4-6` — pins a specific version |
| `inherit` | Same model as the main conversation (default when field is omitted) |

## Model resolution order

When Claude invokes a subagent, the model resolves in this order (first match wins):

1. Per-invocation `model` parameter Claude passes when delegating
2. Subagent definition's `model` frontmatter field
3. `CLAUDE_CODE_SUBAGENT_MODEL` environment variable
4. Main conversation's model

Family aliases in the per-invocation or frontmatter slot resolve to the main conversation's exact
model when it already belongs to that family, preserving an extended-context suffix. On a
non-Anthropic provider where Claude Code cannot identify the main model family, the `opus` alias
also resolves to the main model unless `ANTHROPIC_DEFAULT_OPUS_MODEL` is set. Aliases supplied by
`CLAUDE_CODE_SUBAGENT_MODEL` do not use these exceptions.

`CLAUDE_CODE_SUBAGENT_MODEL` alone does not change built-in Explore or Plan. With
`CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, it overrides ordinary subagent selections, but a conversation
fork and a forked skill with `model: inherit` still use the main conversation model. If only the
force variable is set, Explore retains its Anthropic-API Opus cap.

SOURCE: <https://code.claude.com/docs/en/sub-agents#choose-a-model> (accessed 2026-09-24)

## CLAUDE_CODE_SUBAGENT_MODEL

SOURCE: <https://code.claude.com/docs/en/env-vars.md> (accessed 2026-05-28)
SOURCE: <https://code.claude.com/docs/en/model-config.md> § Environment variables (accessed 2026-05-28)

Provides the default after per-invocation and frontmatter selection:

```bash
export CLAUDE_CODE_SUBAGENT_MODEL=haiku
```

Set to `inherit` to restore normal model resolution:

```bash
export CLAUDE_CODE_SUBAGENT_MODEL=inherit
```

Set `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` to force this configured model over per-invocation and frontmatter selections.

---

## Effort field

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Supported frontmatter fields (accessed 2026-05-28)
SOURCE: <https://code.claude.com/docs/en/model-config.md> § Adjust effort level (accessed 2026-05-28)

The `effort` field overrides the session effort level when this specific subagent is active:

```yaml
effort: high
```

Available levels depend on the model:

| Model | Supported levels |
|:------|:----------------|
| Opus 4.7 | `low`, `medium`, `high`, `xhigh`, `max` |
| Opus 4.6, Sonnet 4.6 | `low`, `medium`, `high`, `max` |

If you set a level the model does not support, Claude Code falls back to the highest supported level at or below the one you set.

### Effort level guidance

| Level | When to use |
|:------|:------------|
| `low` | Latency-sensitive, scoped, non-intelligence-sensitive tasks |
| `medium` | Cost-sensitive work that can trade some intelligence |
| `high` | Standard implementation, file editing, test writing |
| `xhigh` | Best results for most coding and agentic tasks (recommended default on Opus 4.7) |
| `max` | Deep reasoning — may show diminishing returns; session-only (not persistable in settings) |

### Precedence

`CLAUDE_CODE_EFFORT_LEVEL` env var > frontmatter `effort` > session level

The environment variable takes precedence over the frontmatter `effort` field. Frontmatter effort applies only when the subagent is active, overriding the session level.

## CLAUDE_CODE_EFFORT_LEVEL

SOURCE: <https://code.claude.com/docs/en/env-vars.md> (accessed 2026-05-28)

Set the effort level for all models globally:

```bash
export CLAUDE_CODE_EFFORT_LEVEL=high
```

Valid values: `low`, `medium`, `high`, `xhigh`, `max`, or `auto` (model default).

This variable takes precedence over all other effort configuration including `/effort` command and the `effortLevel` setting.
