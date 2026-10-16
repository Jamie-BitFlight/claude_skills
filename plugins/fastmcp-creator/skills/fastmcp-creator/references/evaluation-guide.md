# MCP Server Evaluation Guide [1]

Create evaluations that show whether an LLM can use your MCP server to achieve promised client outcomes.

## Purpose

GOAL: Measure whether an LLM with NO other context and access ONLY to the MCP server can achieve realistic, promised client outcomes.

Every evaluation case must connect to a promised client outcome, a changed tool contract, an acceptance criterion, or a material client risk. The case must state the scenario, the failure it distinguishes, the answer oracle, and the existing environment and cost needed to run it. Keep that admission record in the existing task plan, review, or evaluation notes; the XML file remains only a question and answer.

## Overview

REQUIREMENT: Create enough human-readable questions to cover the admitted outcomes and material risks. Use ONLY READ-ONLY, INDEPENDENT, NON-DESTRUCTIVE, and IDEMPOTENT operations.

Question count and tool-call count are measurements, not targets. Do not add cases merely to reach a fixed count or require long tool sequences merely to make an evaluation harder.

Each question must be:

- Realistic
- Clear and concise
- Unambiguous
- Directly discriminating: a pass rules out a meaningful client or contract failure
- Answerable with a single, verifiable value identified in advance

## Question Guidelines

### Core Requirements

RULE: The model must ensure questions are independent

CONSTRAINT: Each question must NOT depend on answers to other questions or assume prior write operations

RULE: The model must require ONLY NON-DESTRUCTIVE AND IDEMPOTENT tool use

CONSTRAINT: Questions should not instruct or require modifying state to arrive at correct answer

RULE: The model must create REALISTIC, CLEAR, CONCISE questions that discriminate the admitted outcome or risk

CONSTRAINT: Use only the number of calls and steps required by the promised workflow. A single call is valid when it is the cheapest direct check.

### Complexity and Depth

PATTERN: Multi-hop questions requiring multiple sub-questions and sequential tool calls

CONSTRAINT: Use this only when the client outcome requires information from earlier calls.

PATTERN: Paging through multiple pages of results

CONSTRAINT: Use this only when pagination or historical retrieval is part of the promised tool contract or a material client risk.

PATTERN: Deep understanding rather than surface-level knowledge

CONSTRAINT: May pose complex ideas as True/False questions requiring evidence or use multiple-choice format

RULE: The model must test the reasoning or navigation the client outcome requires

CONSTRAINT:

- Do not disguise a direct lookup merely to defeat keyword search
- Use paraphrase, aggregation, or multiple searches only when the client task needs them
- Keep the smallest question that distinguishes the intended failure

### Tool Testing

PATTERN: Questions that exercise a tool's returned data

CONSTRAINT: Exercise large results, filtering, or pagination only when the server promises that behavior or a realistic client outcome depends on it. Keep exploration and evaluation requests caller-bounded.

PATTERN: Questions requiring understanding multiple modalities of data:

- IDs and names
- Timestamps and datetimes (months, days, years, seconds)
- File IDs, names, extensions, and mimetypes
- URLs, GIDs, etc.

RULE: The model must create questions that MOSTLY reflect real human use cases

CONSTRAINT: The kinds of information retrieval tasks that HUMANS assisted by an LLM would care about

PATTERN: Questions requiring several tool calls

CONSTRAINT: Retain the sequence only when removing a call would stop the case from distinguishing its admitted failure.

PATTERN: Include ambiguous questions

CONSTRAINT:

- May be ambiguous OR require difficult decisions on which tools to call
- Force the LLM to potentially make mistakes or misinterpret
- Despite AMBIGUITY, there is STILL A SINGLE VERIFIABLE ANSWER

### Stability

RULE: The model must design questions so answers DO NOT CHANGE

CONSTRAINT:

- Do not ask questions that rely on "current state" which is dynamic
- Do not count: number of reactions to a post, number of replies to a thread, number of members in a channel

RULE: The model must use only the server capabilities needed for an admitted case

CONSTRAINT:

- A case must be answerable with the available read-only tools
- Record an unavailable promised capability as an evidence limit or implementation finding; do not invent an unsupported question
- Questions may require specific output formats (datetime vs. epoch time, JSON vs. MARKDOWN)
- Use the smallest format and retrieval path that gives a stable oracle

## Answer Guidelines

### Verification

RULE: The model must ensure answers are VERIFIABLE via direct string comparison

CONSTRAINT:

- If answer can be re-written in many formats, clearly specify output format in the QUESTION
- Examples: "Use YYYY/MM/DD.", "Respond True or False.", "Answer A, B, C, or D and nothing else."
- Answer should be a single VERIFIABLE value: user ID, user name, display name, channel ID, message ID, URL, numerical quantity, timestamp, boolean, email, file ID, multiple choice answer
- Answers must not require special formatting or complex, structured output
- Answer verified using DIRECT STRING COMPARISON

### Readability

RULE: The model must prefer HUMAN-READABLE formats

CONSTRAINT:

- Examples: names, first name, last name, datetime, file name, message string, URL, yes/no, true/false, a/b/c/d
- Rather than opaque IDs (though IDs are acceptable)
- The VAST MAJORITY of answers should be human-readable

### Stability

RULE: The model must ensure answers are STABLE/STATIONARY

CONSTRAINT:

- Look at old content (conversations that have ended, projects that launched, questions answered)
- Create QUESTIONS based on "closed" concepts that will always return same answer
- Questions may ask to consider fixed time window to insulate from non-stationary answers
- Rely on context UNLIKELY to change
- Be SPECIFIC enough so answer is not confused with later content

### Clarity

RULE: The model must design questions with single, clear answers

CONSTRAINT:

- Questions must be designed so there is a single, clear answer
- Answer can be derived from using the MCP server tools

### Diversity

RULE: The model must ensure answers are DIVERSE

CONSTRAINT:

- Answer should be single VERIFIABLE value in diverse modalities and formats
- User concept: user ID, user name, display name, first name, last name, email address, phone number
- Channel concept: channel ID, channel name, channel topic
- Message concept: message ID, message string, timestamp, month, day, year

RULE: The model must ensure answers are NOT complex structures

CONSTRAINT:

- Not a list of values
- Not a complex object
- Not a list of IDs or strings
- Not natural language text
- UNLESS answer can be straightforwardly verified using DIRECT STRING COMPARISON and can be realistically reproduced
- Unlikely that an LLM would return the same list in any other order or format

## Evaluation Process

### Step 1: Documentation Inspection

PROCEDURE:

1. Read only the documentation needed to identify the promised outcomes, changed contracts, acceptance criteria, and material risks
2. Fetch additional documentation only to resolve a named unanswered task question
3. Stop when the admission record has enough evidence to select the cheapest direct cases
4. If exploration repeats, record the unresolved question or new evidence that justifies it

### Step 2: Tool Inspection

PROCEDURE:

1. List the tools relevant to each admitted case
2. Inspect their input/output schemas, docstrings, and descriptions
3. Record the smallest read-only route that can produce each case's oracle

### Step 3: Developing Understanding

PROCEDURE:

1. Refine a candidate only when an unresolved task question or new evidence can change its admission, oracle, or route
2. At NO stage should you READ the code of the MCP server implementation itself
3. Stop when each retained case has an admitted purpose and a direct oracle

### Step 4: Read-Only Content Inspection

PROCEDURE:

1. USE the MCP server tools
2. Inspect content using READ-ONLY and NON-DESTRUCTIVE operations ONLY
3. Goal: identify the smallest stable content needed for one admitted question at a time
4. Should NOT call any tools that modify state
5. Will NOT read the code of the MCP server implementation itself
6. Keep exploration incremental, small, and targeted
7. Use caller-controlled `limit` and pagination when the tool supports them; do not assume every tool accepts `limit`
8. Continue only while a call can resolve the case's named question or establish its oracle

### Step 5: Task Generation

PROCEDURE:

1. Create one human-readable question for each admitted coverage need, removing duplicates that distinguish the same failure
2. Confirm an LLM can answer it with the MCP server's read-only tools
3. Follow all question and answer guidelines

## Output Format

XML_SCHEMA:

```xml
<evaluation>
  <qa_pair>
    <question>Find the project created in Q2 2024 with the highest number of completed tasks. What is the project name?</question>
    <answer>Website Redesign</answer>
  </qa_pair>
  <qa_pair>
    <question>Search for issues labeled as "bug" that were closed in March 2024. Which user closed the most issues? Provide their username.</question>
    <answer>sarah_dev</answer>
  </qa_pair>
  <qa_pair>
    <question>Look for pull requests that modified files in the /api directory and were merged between January 1 and January 31, 2024. How many different contributors worked on these PRs?</question>
    <answer>7</answer>
  </qa_pair>
</evaluation>
```

## Good Question Examples

### Example 1: Multi-hop exploration

```xml
<qa_pair>
  <question>Find the repository that was archived in Q3 2023 and had previously been the most forked project in the organization. What was the primary programming language used in that repository?</question>
  <answer>Python</answer>
</qa_pair>
```

CHARACTERISTICS:

- Requires multiple searches to find archived repositories
- Needs to identify which had the most forks before archival
- Requires examining repository details for the language
- Answer is simple, verifiable value
- Based on historical (closed) data that won't change

### Example 2: Context without keyword matching

```xml
<qa_pair>
  <question>Locate the initiative focused on improving customer onboarding that was completed in late 2023. The project lead created a retrospective document after completion. What was the lead's role title at that time?</question>
  <answer>Product Manager</answer>
</qa_pair>
```

CHARACTERISTICS:

- Doesn't use specific project name
- Requires finding completed projects from specific timeframe
- Needs to identify the project lead and their role
- Requires understanding context from retrospective documents
- Answer is human-readable and stable
- Based on completed work (won't change)

### Example 3: Complex aggregation

```xml
<qa_pair>
  <question>Among all bugs reported in January 2024 that were marked as critical priority, which assignee resolved the highest percentage of their assigned bugs within 48 hours? Provide the assignee's username.</question>
  <answer>alex_eng</answer>
</qa_pair>
```

CHARACTERISTICS:

- Requires filtering bugs by date, priority, and status
- Needs to group by assignee and calculate resolution rates
- Requires understanding timestamps to determine 48-hour windows
- Tests pagination (potentially many bugs to process)
- Answer is a single username
- Based on historical data from specific time period

## Poor Question Examples

### Example 1: Answer changes over time

```xml
<qa_pair>
  <question>How many open issues are currently assigned to the engineering team?</question>
  <answer>47</answer>
</qa_pair>
```

PROBLEM: Answer will change as issues are created, closed, or reassigned. Not based on stable/stationary data.

### Example 2: Too easy with keyword search

```xml
<qa_pair>
  <question>Find the pull request with title "Add authentication feature" and tell me who created it.</question>
  <answer>developer123</answer>
</qa_pair>
```

PROBLEM: Can be solved with straightforward keyword search for exact title. Doesn't require deep exploration or understanding.

### Example 3: Ambiguous answer format

```xml
<qa_pair>
  <question>List all the repositories that have Python as their primary language.</question>
  <answer>repo1, repo2, repo3, data-pipeline, ml-tools</answer>
</qa_pair>
```

PROBLEM: Answer is a list that could be returned in any order. Difficult to verify with direct string comparison. Better to ask for specific aggregate or superlative.

## Verification Process

PROCEDURE:

1. Examine the XML file to understand the schema
2. Load each task instruction and in parallel using MCP server and tools, identify correct answer by attempting to solve the task YOURSELF
3. Flag any operations that require WRITE or DESTRUCTIVE operations
4. Accumulate all CORRECT answers and replace any incorrect answers in the document
5. Remove any `<qa_pair>` that requires WRITE or DESTRUCTIVE operations, lacks an admitted outcome or risk, or cannot distinguish a material failure

CONSTRAINT: Preserve the XML schema of `<question>` and `<answer>`. Keep coverage and admission rationale in the existing task record rather than adding evaluation-only fields or tools.

## Evaluation Scripts

The skill includes scripts for running evaluations using the evaluation harness.

LOCATION: `./scripts/`

FILES:

- `evaluation.py` - Evaluation harness script
- `connections.py` - MCP connection utilities
- `requirements.txt` - Python dependencies
- `example_evaluation.xml` - Example evaluation file

SETUP:

```bash
pip install -r scripts/requirements.txt
export ANTHROPIC_API_KEY=your_api_key_here
```

USAGE:

```bash
# For STDIO servers (script launches server automatically)
python scripts/evaluation.py \
  -t stdio \
  -c python \
  -a my_mcp_server.py \
  evaluation.xml

# For SSE/HTTP servers (you must start server first)
python scripts/evaluation.py \
  -t sse \
  -u https://example.com/mcp \
  -H "Authorization: Bearer token123" \
  evaluation.xml
```

See evaluation.py source code for complete command-line options and transport types.

## Tips for Quality Evaluations

1. **Start from task intent**: admit each case through an outcome, contract, criterion, or material risk.
2. **Use the cheapest discriminator**: avoid extra calls, cases, or environments that do not change the decision.
3. **Focus on realistic use cases** that humans would actually want to accomplish.
4. **Ensure stability** by using historical data and closed concepts.
5. **Verify answers** by solving each retained question with MCP server tools.
6. **Refine only on evidence**: an unresolved task question or new evidence must justify another exploration or evaluation pass.

## Summary

Evaluation creation is critical for MCP server quality. Follow these guidelines to create evaluations that:

- Test real-world usage patterns
- Challenge the LLM's ability to use tools effectively
- Provide verifiable, stable answers
- Guide improvement of tool design and documentation

## Sources

- [FastMCP GitHub Repository (PrefectHQ/fastmcp)](https://github.com/prefecthq/fastmcp) (accessed 2026-02-22)
- [FastMCP Official Documentation](https://gofastmcp.com/) (accessed 2026-02-22)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/) (accessed 2026-02-22)

## References

1. [Model Context Protocol Documentation](https://modelcontextprotocol.io/docs) (accessed 2026-06-07)
