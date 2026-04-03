# Utilization Proposals: Mission Control

**Research entry**: ./research/agent-frameworks/mission-control.md
**Generated**: 2026-04-03
**Integration surfaces found**: 4 (REST API | WebSocket | Webhooks | NPM package)
**Proposals written**: 2
**Skipped**: 3 — research-curator (no cost tracking API consumption needed), backlog-tools-administrator (orthogonal scope), swarm-spawning (no external orchestration service needed)

---

## Utilization 1: swarm-orchestrating → Mission Control Cost Tracking API

**Research entry**: ./research/agent-frameworks/mission-control.md
**Caller**: ./.claude/skills/swarm-orchestrating/SKILL.md and ./.claude/skills/swarm-operations/SKILL.md
**Integration mechanism**: HTTP REST API call
**Replaces or adds**: Adds cost visibility and budget enforcement to Claude Code swarms that run at scale
**Setup cost**: Medium (API endpoint discovery, auth token configuration, cost model mapping)
**Integration surface**: `POST /api/tasks/{TASK_ID}` with cost tracking fields; `GET /api/health/metrics` for Prometheus metrics; per-task cost aggregation via Mission Control database

### Why this caller

The `swarm-orchestrating` and `swarm-operations` skills document multi-agent execution patterns (parallel specialists, pipeline, convoy mode from Mission Control v2.3+) but do not address cost visibility. When orchestrating teams of 3-5 agents running simultaneously (Convoy Mode pattern, per research lines 72-80), costs accumulate rapidly and are invisible to the orchestrator. Mission Control's cost tracking engine (documented lines 240-244) records per-task costs broken down by agent, model, and token count with daily/monthly cap enforcement. Integrating with this API would allow Claude Code swarms to:

1. Track costs per-agent per-task in real-time
2. Enforce budget caps before spawning parallel agents
3. Report cost-per-priority-level (design vs. build vs. test)

Currently, Claude Code swarms have no built-in cost tracking beyond model-wide aggregates. This surfaces a gap: operators cannot determine which agent or task phase consumed the budget.

### Integration sketch

Pseudo-code for cost tracking integration into swarm operations:

```python
# In swarm_orchestrating skill or operations module
async def spawn_convoy_with_cost_tracking(team_config, agents_to_spawn, mission_control_url):
    # 1. Create task in Mission Control with budget cap
    task_id = await post_to_mission_control(
        f"{mission_control_url}/api/tasks",
        payload={
            "title": team_config["team_name"],
            "cost_cap_usd": 50.0,  # from swarm config
            "agents": len(agents_to_spawn)
        },
        headers={"Authorization": f"Bearer {MC_API_TOKEN}"}
    )

    # 2. Spawn agents locally, tagging them with task_id
    for agent in agents_to_spawn:
        Agent(
            team_name=team_config["team_name"],
            name=agent["name"],
            subagent_type=agent["type"],
            prompt=agent["prompt"],
            env={"MC_TASK_ID": task_id, "MC_URL": mission_control_url}
        )

    # 3. Periodically check cost cap
    async def poll_cost():
        while team_active:
            cost_resp = await get_from_mission_control(
                f"{mission_control_url}/api/tasks/{task_id}",
                headers={"Authorization": f"Bearer {MC_API_TOKEN}"}
            )
            if cost_resp["cost_usd"] > cost_resp["cost_cap_usd"]:
                SendMessage(type="broadcast", content="Cost cap exceeded — shutting down")
                TeamDelete()
                break
            await sleep(30)
```

The research entry documents the exact API contract (lines 263-276) needed to implement this: task registration via `POST /api/tasks/{TASK_ID}`, cost retrieval via endpoints, and health metrics via `GET /api/health/metrics`.

**Integration blockers**: Mission Control requires OpenClaw Gateway for agent dispatch (line 429), which Claude Code does not use. The cost tracking API itself is decoupled from agent runtime and can be called independently, but operators would need to host Mission Control separately to use the cost API.

---

## Utilization 2: research-curator → Mission Control Knowledge Injection Pattern

**Research entry**: ./research/agent-frameworks/mission-control.md
**Caller**: ./.claude/agents/research-curator.md
**Integration mechanism**: Pattern adoption (no external service call required; pattern is implemented locally)
**Replaces or adds**: Adds knowledge extraction and injection loop to research workflow — research-curator currently produces entries with confidence metadata but does not feed learnings back into future research cycles
**Setup cost**: Low (pattern adoption in research-curator agent prompt; knowledge base file structure already exists)
**Integration surface**: Mission Control's Learner agent pattern (lines 99-102) and knowledge entry nullification on task deletion (line 103); pattern described in research lines 99-103

### Why this caller

The `research-curator` agent (per agent file lines 1-3) "gathers information from primary sources using MCP tools" and produces structured research entries with confidence levels. However, it does not currently capture lessons learned or feed discoveries back into future research iterations. This is a closed-loop opportunity: when research-curator discovers that a pattern works well or a claim requires revision, that discovery should influence the next research cycle to avoid repeating the same investigation.

Mission Control's Learner agent (research lines 99-102) captures lessons from every build cycle: "what worked, what failed, what patterns emerged." The pattern is: "Knowledge entries are injected into future dispatches so agents don't repeat mistakes" (line 102). Applying this pattern to research-curator would mean:

1. After each research entry completes, extract reusable lessons (e.g., "This API has poor documentation — check for GitHub discussions instead of official docs")
2. Store lessons in a per-category knowledge base
3. Inject relevant lessons into the next research-curator invocation in the same category

Currently, research-curator has no mechanism to learn from prior research in the same domain — each invocation starts fresh.

### Integration sketch

Pattern implementation in research-curator agent prompt:

```markdown
## Knowledge Injection Phase (Added)

Before starting research, load the knowledge base for this category:

1. Read ./research/insights/{category}-knowledge.md if it exists
2. Extract lessons in the "What We Learned" section
3. Prepend these lessons to your research plan:
   - Skip sources that prior research marked as "unreliable"
   - Prioritize sources marked as "authoritative" or "has undocumented APIs"
   - Follow patterns that "reduced research time" or "uncovered hidden features"

## Knowledge Capture Phase (Added)

After completing research, append to ./research/insights/{category}-knowledge.md:

- **Discovery**: [What did you learn that will help future research in this category?]
  Example: "This project's API is documented in ORCHESTRATION.md, not README.md"
  Example: "GitHub search found 10+ undocumented CLI flags not in package.json"

- **Time Saver**: [What approach saved time or revealed information faster?]
  Example: "Checked CHANGELOG.md for architectural changes before reading README"

- **Unreliable Source**: [What source was incomplete or outdated?]
  Example: "Live demo was 3 versions behind; check GitHub releases for latest behavior"

Lessons are nullified when the parent research entry is deleted (preventing stale knowledge).
```

The research entry documents the knowledge pattern at high level (lines 99-102) with sufficient detail to implement pattern adoption. Unlike the cost-tracking proposal, this proposal requires no external service and no API integration — it is purely a workflow enhancement using existing Claude Code file structures.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| ./.claude/agents/research-curator.md | Research-curator is a researcher, not a cost tracker. Integration opportunity exists only if Mission Control knowledge base API were documented; current research entry describes knowledge injection pattern but not API contract for knowledge retrieval/storage. Deferred until knowledge API is documented. |
| ./.claude/skills/backlog-tools-administrator/SKILL.md | Scope orthogonal — backlog-tools-administrator manages backlog tooling (script, process, documentation gaps), not external cost tracking services. Mission Control cost tracking applies to swarm execution, not backlog metadata. |
| ./.claude/skills/swarm-spawning/SKILL.md | Swarm-spawning documents agent creation mechanics but does not orchestrate external task dispatch services. Mission Control's task API and agent dispatch happen upstream of spawning; no integration point where swarm-spawning itself needs to call Mission Control APIs. Cost enforcement and monitoring (Utilization 1) is handled by swarm-orchestrating, not by the spawn mechanism. |

---

## Integration Opportunity Not Pursued (GitHub Webhooks)

**Research entry documents**: Automated rollback pipeline via GitHub webhooks (lines 148-152)
**Why skipped**: Claude Code has no local equivalent to the "merged PR health check → auto-revert" pattern. This would require integrating with Claude Code's PR workflow and adding a rollback mechanism, which is architectural scope larger than a single skill/agent integration. The research entry documents the pattern clearly (lines 150-152) but implementing it in Claude Code would require creating a new GitHub Actions workflow or webhook receiver, not just consuming an external API.

This is a **pattern adoption opportunity** (not a utilization opportunity per se) and should be tracked separately as an architectural enhancement.

