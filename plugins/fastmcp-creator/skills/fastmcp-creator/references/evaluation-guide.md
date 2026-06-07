# MCP Server Evaluation Guide [1]

Complete guide for creating comprehensive evaluations to test whether LLMs can effectively use your MCP server to answer realistic, complex questions.

## Purpose

GOAL: The measure of MCP server quality is how well implementations enable LLMs with NO other context and access ONLY to the MCP server to answer realistic and difficult questions.

## Overview

REQUIREMENT: Create 10 human-readable questions requiring ONLY READ-ONLY, INDEPENDENT, NON-DESTRUCTIVE, and IDEMPOTENT operations to answer.

Each question must be:

- Realistic
- Clear and concise
- Unambiguous
- Complex (requiring potentially dozens of tool calls or steps)
- Answerable with a single, verifiable value identified in advance

## Question Guidelines

### Core Requirements

RULE: The model must ensure questions are independent

CONSTRAINT: Each question must NOT depend on answers to other questions or assume prior write operations

RULE: The model must require ONLY NON-DESTRUCTIVE AND IDEMPOTENT tool use

CONSTRAINT: Questions should not instruct or require modifying state to arrive at correct answer

RULE: The model must create REALISTIC, CLEAR, CONCISE, and COMPLEX questions

CONSTRAINT: Must require another LLM to use multiple (potentially dozens of) tools or steps to answer

### Complexity and Depth

PATTERN: Multi-hop questions requiring multiple sub-questions and sequential tool calls

CONSTRAINT: Each step should benefit from information found in previous questions

PATTERN: Extensive paging through multiple pages of results

CONSTRAINT: May require querying old data (1-2 years out-of-date) to find niche information

PATTERN: Deep understanding rather than surface-level knowledge

CONSTRAINT: May pose complex ideas as True/False questions requiring evidence or use multiple-choice format

RULE: The model must NOT make questions solvable with straightforward keyword search

CONSTRAINT:

- Do not include specific keywords from target content
- Use synonyms, related concepts, or paraphrases
- Require multiple searches, analyzing multiple related items, extracting context, then deriving answer

### Tool Testing

PATTERN: Questions that stress-test tool return values

CONSTRAINT: May elicit tools returning large JSON objects or lists, overwhelming the LLM

PATTERN: Questions requiring understanding multiple modalities of data:

- IDs and names
- Timestamps and datetimes (months, days, years, seconds)
- File IDs, names, extensions, and mimetypes
- URLs, GIDs, etc.

RULE: The model must create questions that MOSTLY reflect real human use cases

CONSTRAINT: The kinds of information retrieval tasks that HUMANS assisted by an LLM would care about

PATTERN: Questions that may require dozens of tool calls

CONSTRAINT: This challenges LLMs with limited context and encourages MCP server tools to reduce information returned

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

RULE: The model must NOT let the MCP server RESTRICT the kinds of questions created

CONSTRAINT:

- Create challenging and complex questions
- Some may not be solvable with available MCP server tools
- Questions may require specific output formats (datetime vs. epoch time, JSON vs. MARKDOWN)
- Questions may require dozens of tool calls to complete

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

1. Read documentation of target API to understand available endpoints and functionality
2. If ambiguity exists, fetch additional information from the web
3. Parallelize this step AS MUCH AS POSSIBLE
4. Ensure each subagent is ONLY examining documentation from file system or web

### Step 2: Tool Inspection

PROCEDURE:

1. List tools available in the MCP server
2. Inspect the MCP server directly
3. Understand input/output schemas, docstrings, and descriptions
4. WITHOUT calling the tools themselves at this stage

### Step 3: Developing Understanding

PROCEDURE:

1. Repeat steps 1 & 2 until you have good understanding
2. Iterate multiple times
3. Think about the kinds of tasks you want to create
4. Refine your understanding
5. At NO stage should you READ the code of the MCP server implementation itself
6. Use intuition and understanding to create reasonable, realistic, but VERY challenging tasks

### Step 4: Read-Only Content Inspection

PROCEDURE:

1. USE the MCP server tools
2. Inspect content using READ-ONLY and NON-DESTRUCTIVE operations ONLY
3. Goal: identify specific content for creating realistic questions
4. Should NOT call any tools that modify state
5. Will NOT read the code of the MCP server implementation itself
6. Parallelize this step with individual sub-agents pursuing independent explorations
7. Ensure each subagent is only performing READ-ONLY, NON-DESTRUCTIVE, and IDEMPOTENT operations
8. BE CAREFUL: SOME TOOLS may return LOTS OF DATA causing you to run out of CONTEXT
9. Make INCREMENTAL, SMALL, AND TARGETED tool calls for exploration
10. In all tool call requests, use the `limit` parameter to limit results (<10)
11. Use pagination

### Step 5: Task Generation

PROCEDURE:

1. After inspecting the content, create 10 human-readable questions
2. An LLM should be able to answer these with the MCP server
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
5. Remove any `<qa_pair>` that require WRITE or DESTRUCTIVE operations

CONSTRAINT: Parallelize solving tasks to avoid running out of context, then accumulate all answers and make changes to file at the end

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

1. **Think Hard and Plan Ahead** before generating tasks
2. **Parallelize Where Opportunity Arises** to speed up process and manage context
3. **Focus on Realistic Use Cases** that humans would actually want to accomplish
4. **Create Challenging Questions** that test limits of MCP server's capabilities
5. **Ensure Stability** by using historical data and closed concepts
6. **Verify Answers** by solving questions yourself using MCP server tools
7. **Iterate and Refine** based on what you learn during process

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
