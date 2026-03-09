# RTFP — Original Design Spec

> Source: user message 2026-03-09. This is the authoritative spec.
> Use this file to audit all plugin files for conformance.

---

RTFP: Read The Fucking Prompt is a plugin for Claude Code that scans Claude Code session transcripts to find the strongest user reactions to instruction-following failures, reconstructs the assistant output that triggered them, and turns the best exchange into a shareable terminal-style artifact.

## Constraints

- Claude Code session data is stored in JSONL files on disk.
- JSONL is the storage layer.
- DuckDB is the query layer used to inspect and query session data directly.
- The AI assistant can start subagents.
- Subagents can run MCP tools or scripts.
- In the first-pass batching stage, batch files must contain only user-authored messages.
- Do not include assistant messages, tool outputs, system messages, developer messages, or any other non-user entries in those batch files.
- Each batched entry must still preserve its original source session file path and original message index id so it can be traced back later.

## Workflow

The AI assistant receives the user's request.

The AI assistant finds and presents a list of recent sessions from the current project, including their titles.

The user chooses which session to inspect.

Once the session is selected, the AI assistant starts a processing loop.

### Stage 1: User-only extraction and batching

- Read the selected session JSONL.
- Filter the transcript down to user-authored messages only.
- Exclude every non-user message from the batch input.
- Create temporary batch files of about 100k tokens each using only those user-authored messages.
- Every entry in every batch file must include:
  - source session file path
  - original message index id
  - user message text

The purpose of the first pass is only to detect emotional user replies at scale.
It is not for contextual reconstruction.
Do not include full transcript context in the batch files.

### Stage 2: Subagent detection over user-only batch files

For each temporary batch file, the AI assistant starts a subagent.

Each subagent reads only its assigned user-only batch file and identifies user messages that contain strong emotional reactions aimed at the assistant, including frustration, disappointment, disbelief, argument, insults, or other clearly negative emotional responses.

Each subagent returns:

1. A JSON file containing the flagged message indexes grouped by source file
2. A plain list of the flagged entries it found

The parent AI assistant then merges the returned index ids together per file into a single working set.

### Stage 3: Reconstruct context only after candidate selection

That merged working set is then given to another agent whose job is to read all of the flagged user responses and choose:

1. The single most emotional, rage-filled response
2. A runner-up as well, if there are multiple strong spicy responses

Only at this stage should the system go back to the full session transcript.

That same agent must then:

1. Retrieve each flagged user message from the full session
2. Inspect nearby transcript entries
3. Determine the current activity or task the user and assistant were in the middle of doing
4. Identify the assistant message or messages that triggered the user's reaction

The summary should be a dry background line that sets the scene.
It is not a summary of the misunderstanding.
It is not a diagnosis.
It is not a root-cause explanation.
It is just the short setup of what they were doing.

Example style:
`task: writing a Claude Code plugin`

### Output artifact

The final artifact should contain:

1. The short dry task summary
2. The assistant output that triggered the reaction
3. The user's emotional reply

The output should be rendered as a PNG that looks like a terminal interface and is ready to paste into social media.

## Anti-requirements

- Do not turn this into a generic analytics tool.
- Do not build a broad taxonomy.
- Do not add scoring.
- Do not add verdicts.
- Do not add extra evaluative layers unless explicitly requested.
- Do not include full transcript messages in first-pass batch files.
- The first-pass batch files are user-only detection inputs.
- Context reconstruction happens later, after candidate user messages have already been flagged.

## The point

Capture one clean moment:
- what they were doing
- what the assistant said
- how the user reacted
