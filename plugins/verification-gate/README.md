<p align="center">
  <img src="./assets/hero.png" alt="Verification Gate" width="800" />
</p>

# Verification Gate

Makes the agent investigate before acting instead of jumping to pattern-matched solutions.

## Why Install This?

The agent sometimes identifies the problem correctly but applies the wrong fix. This happens when the agent recognizes an error pattern and immediately applies a "standard solution" from its training data without checking if that solution matches your specific project setup.

Examples of what goes wrong without this plugin:

- You get "module not found" on a PEP 723 script. The agent runs `uv sync` (which targets `pyproject.toml`, not the PEP 723 inline dependencies)
- Your config is not loading. The agent modifies the config file without checking that your app reads environment variables instead
- A package will not import. The agent runs `pip install` globally when your script uses a virtualenv
- A build fails. The agent applies a fix from its training data before reading the actual error output

## How It Works

This plugin installs a skill that enforces four mandatory checkpoints before any implementation action (Bash, Write, Edit, or other write-capable actions):

**Checkpoint 1: Hypothesis Stated** — The agent must state a specific, falsifiable hypothesis about what is wrong and what system it targets.

**Checkpoint 2: Hypothesis Verified** — The agent must gather evidence (read files, check docs, run read-only commands) that confirms or refutes the hypothesis. Cannot proceed on a guess.

**Checkpoint 3: Hypothesis-Action Alignment** — The agent verifies that the proposed fix actually targets the same system the hypothesis identified. Blocks "correct diagnosis, wrong fix" errors.

**Checkpoint 4: Pattern-Matching Detection** — The agent checks whether it is about to apply a "common solution" without verifying that pattern applies here. Forces a project-specific check.

Only when all four checkpoints pass does the agent execute. If any checkpoint fails, the agent halts and reports what it needs before it can proceed.

## What Changes

With this plugin installed, the agent will:

- Read relevant files before trying to fix things
- State a specific hypothesis before gathering evidence
- Verify the diagnosis with file reads, not assumptions
- Check that the fix targets the same system as the diagnosis
- Detect when it is about to apply a training-data pattern to a context it has not verified

This makes the agent slower to start but much more accurate — fewer debugging cycles overall.

## Installation

First, add the marketplace (one-time setup):

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
```

Then install the plugin:

```bash
/plugin install verification-gate@jamie-bitflight-skills
```

## Usage

Just install it — it works automatically. You will notice the difference when the agent:

- Reads files before running commands
- States what it thinks the problem is before gathering evidence
- Explains what system it is targeting before making changes
- Pauses and reports what it needs when it cannot verify something

## Example

**Without this plugin:**

```
You: This PEP 723 script can't find the pydantic module
Agent: I'll install the dependencies
Agent: [Runs uv sync immediately]
Result: Doesn't work - uv sync operates on pyproject.toml, not PEP 723
```

**With this plugin:**

```
You: This PEP 723 script can't find the pydantic module
Agent: Hypothesis: pydantic is missing from the script's inline dependencies.
       Verifying — need to check whether this script uses PEP 723 metadata.
Agent: [Reads the script file]
Agent: Confirmed: PEP 723 inline dependencies block present. pydantic is not listed.
       Fix target: the # /// script block in the file. Running uv add --script.
Agent: [Runs: uv add --script example.py pydantic]
Result: Works correctly
```

Another example:

**Without this plugin:**

```
You: The app can't connect to the database
Agent: [Immediately edits database config file]
Result: Config change ignored — app reads DATABASE_URL from environment variables
```

**With this plugin:**

```
You: The app can't connect to the database
Agent: Hypothesis: database connection string is misconfigured.
       Need to verify which configuration system the app uses.
Agent: [Reads app.py, config.py, checks for dotenv or os.environ usage]
Agent: App reads DATABASE_URL from environment, not config file.
       Fix target: environment variable, not config file.
Agent: [Checks .env file, identifies missing variable]
```

## Skill

The plugin installs the `verification-gate` skill, which activates automatically when the agent is about to execute implementation actions. The skill enforces the four-checkpoint protocol and integrates with workspace verification rules.

## Trade-offs

- The agent will be slower to start (2-4 extra file reads before each action)
- The agent will explain its reasoning more (adds verbosity)
- Fixes will be more accurate (fewer debugging cycles)
- Overall time saved despite the slower start

## Requirements

- A Codex- or Claude-compatible workflow that supports the listed implementation actions
