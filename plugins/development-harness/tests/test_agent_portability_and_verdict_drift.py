"""Guards agent definitions against re-binding to one checkout, and the alignment verdict set.

An agent definition in ``agents/`` is prompt text shipped to whatever repository installs this
plugin. Anything in it that names *this* checkout — a repository slug, a path that only resolves
from this directory layout — is correct here and wrong everywhere else, and nothing about running
it here reveals that. The portability shapes guarded below are the ones that were actually found:

- ``agents/alignment-analyst.md`` ran ``gh pr list -R <owner>/<repo>`` against the plugin author's
  repository. Installed anywhere else it queried the wrong project's history and reported the
  answer as the installing project's direction. Repositories are resolved through the configured
  backend (``backlog_list_merged_prs``), never written into a prompt.
- ``agents/plan-validator.md`` and ``agents/swarm-task-planner.md`` cited the ``dh:execution``
  skill as ``plugins/development-harness/skills/execution/SKILL.md``. A plugin-rooted path
  resolves only from a checkout laid out like this one; the skill name resolves wherever the agent
  runs. This is ``rules/markdown-file-references.md``'s Skill Activation References rule. Note it
  is a portability rule and not a gate: ``ARCHITECTURE.md`` states that a skill an instruction
  names is not a Tier-1 decomposition-gate referent, so nothing else checks these citations.
  A later sweep found the same shape inside ``skills/`` itself — one skill citing a sibling skill
  by its plugin-rooted path is the identical checkout-binding defect, so the guard now scans
  ``skills/`` too. ``SKILL_PATH_CITATION_EXCEPTIONS`` names the two files where the matched text is
  not this defect — a naming-convention table stating a path as data, and a labelled anti-pattern
  example — each with the reason it is not a citation to fix.
- ``agents/alignment-analyst.md`` and ``agents/impact-analyst.md`` each carried a byte-identical
  shell snippet that re-derived the active backend inline: ``BACKLOG_BACKEND`` when set, else a
  ``.beads`` *directory*, else ``github``. It skipped ``.dh/config.yaml`` entirely and tested for
  the directory rather than the ``.beads/dh-backend`` opt-in marker, so a project with a stray
  ``.beads`` directory and a configured ``github`` backend resolved to beads. Unlike the two above
  this is not a checkout-binding — the snippet is portable and simply wrong — but it has the same
  failure signature: a wrong answer indistinguishable from a right one at the point it is made.
  The fix is ``rules/shared-process-extraction.md``'s: the procedure moved into the
  ``dh:backend-resolution`` skill, which each agent loads through its ``skills:`` frontmatter, and
  ``docs/backend-providers.md`` under "One configured backend" remains the canonical description
  of the contract that ``create_backend()`` (``backlog_core/backend_protocol.py``) implements.
  Note the guard covers prose as well as shell. Replacing the snippet with a paragraph restating
  the chain was the first attempt at this fix, and it is the same two-copies-free-to-drift defect
  in a medium that is harder to grep for — so the test convicts on the process text, not on one
  spelling of it.

- ``dh:dh-cli-usage`` replaces the ``${CLAUDE_PLUGIN_ROOT}``/``${CLAUDE_SKILL_DIR}`` template
  variables and the CLI's literal ``/sam_schema/cli.py`` path with one skill that derives both from
  its own directory (a ``<skill_dir>`` tag per harness that substitutes one, resolved to
  ``<plugin_root/>`` and ``<sam_cli/>``). A raw template variable in an agent or skill body is the
  same checkout-binding defect as the plugin-rooted skill path above -- a substitution Claude Code
  performs that no other measured harness does, per ``SP/design-agent-cli-path.md`` section 0-1 --
  so it is guarded the same way: a static scan with a named-reason exception table, not a runtime
  check. The guide these agents and skills pointed readers at moves with it, from
  ``dh-meta-docs/references/dh-cli-usage-guide.md`` to
  ``dh-cli-usage/references/command-reference.md``, so a lingering reference to either the old name
  or the old ``docs/mcp-connection-check.md`` path is the same drift this file already convicts
  elsewhere: a pointer nothing keeps in sync with where its target actually lives.

The last guard is a producer contract rather than a portability one. ``alignment-analyst`` used to
be told to emit ``MISSION_DIVERGENT`` for its ``NOT_APPLICABLE`` case — "I could not check this"
and "I checked this and found divergence" arrived as the same token, so a check that never ran was
indistinguishable from a finding. Nothing downstream gated on the token, which is why the
conflation survived: ``agents/rtica-assessor.md`` never reads the section,
``agents/backlog-item-groomer.md`` only lists it among the sections it may find,
``groom/swarm.md``'s Wave 2 gate reads ``rtica-assessor``'s ``Decision:`` token, and
``groom/finalize.md`` validates the section body's ``Alignment assessment:`` field. The absence of
a consumer is why this has to be a test: there is no gate to fail loudly when it regresses.

The shape here follows ``test_rtica_verdict_vocabulary_drift.py``, this plugin's established
guard for a grooming-swarm agent's producer/consumer vocabulary. Every test is a plain test;
nothing is marked xfail, for the reason that module records.
"""

from __future__ import annotations

import re
from pathlib import Path

from agent_profile.parser import _load_frontmatter_from_path, _normalize_skills

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = PLUGIN_ROOT / "agents"
SKILLS_DIR = PLUGIN_ROOT / "skills"

ALIGNMENT_ANALYST = AGENTS_DIR / "alignment-analyst.md"

# The section body field that ``groom/finalize.md``'s validation gate matches, and the three values
# it accepts. This is the one part of the report a consumer does read.
ASSESSMENT_FIELD = "Alignment assessment:"
ASSESSMENT_VALUES = frozenset({"ALIGNED", "DIVERGENT", "NOT_APPLICABLE"})

# One verdict token per assessment value, so a reader of the leading line learns the same thing the
# section body says. Distinctness is the property; the spellings are this agent's own.
VERDICT_TOKENS = frozenset({"MISSION_ALIGNED", "MISSION_DIVERGENT", "MISSION_UNASSESSED"})

# A repository named in prompt text: a ``gh`` repo flag carrying a literal ``owner/name``, or a
# github.com URL doing the same. A placeholder in angle brackets or braces is not a literal.
REPO_SLUG_RE = re.compile(r"(?:(?:-R|--repo)[= ]+|github\.com/)(?P<slug>[A-Za-z0-9][\w.-]*/[A-Za-z0-9][\w.-]*)")

# A skill cited by its plugin-rooted file path. A wildcard segment is a glob describing a class of
# files, not a citation of one skill, so it is not matched.
SKILL_PATH_RE = re.compile(r"plugins/[\w.-]+/skills/[\w.-]+/SKILL\.md")

# Files where matched text is not the citation this guard convicts, each with why. An entry here
# excuses a file from ``test_no_agent_or_skill_cites_a_skill_by_plugin_rooted_path`` entirely, so
# every one names the reason the match is not a portability defect — an allowlist with no reason is
# indistinguishable from an oversight the next person deletes.
SKILL_PATH_CITATION_EXCEPTIONS: dict[Path, str] = {
    SKILLS_DIR / "dh-meta-docs" / "references" / "sdlc-stage-taxonomy.md": (
        "This file's subject is the skill-directory naming convention itself, not a pointer to "
        "load a skill for its content: each stage row and the Section 2 rule state, as data, the "
        "literal SKILL.md path a stage's bare directory name produces — the Section 2 example even "
        "pairs a correct path with a deliberately wrong one that names no real skill. Activation "
        "syntax names a skill to invoke; it cannot state the directory-naming fact these paths "
        "exist to specify, so substituting it would delete the information the row carries."
    ),
    SKILLS_DIR / "code-review-claude-skills" / "SKILL.md": (
        "Line 89's plugin-rooted path sits inside a fenced ``<!-- WRONG: cross-skill backtick path "
        "reference -->`` example, paired with a ``<!-- RIGHT -->`` line showing the activation-"
        "syntax form directly beneath it. This skill's job is teaching reviewers to catch exactly "
        "this citation shape in other skills; rewriting the WRONG line to match the RIGHT one "
        "deletes the contrast the anti-pattern section exists to show."
    ),
}

# --- Backend chain re-derived inline, in either medium ------------------------------------------
#
# ``rules/shared-process-extraction.md`` bans the process text itself, not one spelling of it: an
# agent loads ``dh:backend-resolution`` instead of carrying the chain. A duplicated shell block and
# a duplicated paragraph are the same defect, so this file needs a detector for each. They are
# separate mechanisms because the two media leave different traces, and neither one finds the
# other's shape.
#
# Medium 1 — shell. The removed snippet evaluated a step locally: a parameter expansion reading
# ``BACKLOG_BACKEND`` into a variable, and a ``-d`` test on the ``.beads`` directory.
BACKEND_ENV_EXPANSION_RE = re.compile(r"\$\{BACKLOG_BACKEND\b")

# The opt-in marker ``.beads/dh-backend`` is a file and would be tested with ``-f``, but the
# lookahead excludes the path form explicitly so that a future ``-d .beads/something`` is not swept
# in as if it were the directory-presence bug.
BEADS_DIR_TEST_RE = re.compile(r"-d\s+[\"']?\.beads[\"']?(?!/)")

BACKEND_DERIVATION_PATTERNS = (BACKEND_ENV_EXPANSION_RE, BEADS_DIR_TEST_RE)

# Medium 2 — prose. A restatement cannot be recognised by any one token, because each token it
# contains has a legitimate solo use. What distinguishes it is that it *enumerates*: it walks the
# reader through the steps, so it names several of them together. So the detector counts how many
# distinct steps of the chain a file names and convicts on breadth, not on any single mention.
#
# The threshold is calibrated against the corpus rather than guessed. At the commit before this
# guard, ``alignment-analyst.md`` carried the restatement and named all four; the two legitimate
# mentions that must not be flagged — ``feature-verifier.md`` and ``integration-checker.md``, each
# a prose note that ``BACKLOG_BACKEND=beads`` makes ``issue_number`` a string — named exactly one
# each. No agent named two or three, so any threshold in 2..4 separates them; 2 is chosen because
# naming two steps together is already an enumeration, and a reference needs none of them.
CHAIN_STEP_MARKERS: dict[str, re.Pattern[str]] = {
    "BACKLOG_BACKEND env var": re.compile(r"BACKLOG_BACKEND"),
    ".dh/config.yaml": re.compile(r"\.dh/config\.yaml"),
    ".beads opt-in": re.compile(r"\.beads/dh-backend|\.beads`? ?(?:directory|dir|folder)"),
    "config keys": re.compile(r"backlog\.backend|backend\.name"),
}

# Two distinct steps named in one agent file is an enumeration of the chain. One is a mention.
CHAIN_ENUMERATION_THRESHOLD = 2

# A verdict line as the agent is told to emit it: at the start of a line, inside a fenced block.
EMITTED_VERDICT_RE = re.compile(r"^(MISSION_[A-Z_]+):", re.MULTILINE)

# Every ``MISSION_`` token appearing anywhere in the file, emitted or discussed in prose.
ANY_VERDICT_RE = re.compile(r"MISSION_[A-Z_]+")


# --- Plugin-root variable and hard-coded CLI path (W2, dh-cli-usage) ----------------------------
#
# ``dh:dh-cli-usage`` is the one place that derives the plugin root and the CLI's location. Every
# other agent and skill file is meant to say ``<sam_cli/>`` or ``<plugin_root/>/…`` and point at
# that skill, never re-derive either value itself. These patterns are the two ways a file did that
# derivation directly instead: a raw ``${...PLUGIN_ROOT}`` template variable, and the CLI's literal
# path. See SP/design-agent-cli-path.md section 0 for why -- those template variables are
# substituted by Claude Code only, so every reference and doc file carrying one as raw text ships
# broken text to every other harness. ``dh-cli-usage`` instead derives the root from the skill's
# own directory, which every measured harness gives the model except Cursor (section 1).
PLUGIN_ROOT_VARIABLE_RE = re.compile(r"\$\{(?:CLAUDE_|KIMI_)?PLUGIN_ROOT\}")
PREFIXED_CLI_PATH_RE = re.compile(r"/sam_schema/cli\.py")
AGENT_RELATIVE_LINK_RE = re.compile(r"\]\(\.\.?/")
CLI_INVOCATION_RE = re.compile(r"<sam_cli/>|sam_schema/cli\.py")
TEMPLATE_VARIABLE_RE = re.compile(r"\$\{([A-Za-z_]+)\}")

DH_CLI_USAGE_DIR = SKILLS_DIR / "dh-cli-usage"
DH_CLI_USAGE = DH_CLI_USAGE_DIR / "SKILL.md"
DH_CLI_USAGE_SKILL_URI = "dh:dh-cli-usage"

# The three forms a harness substitutes a skill's own directory into its body as, per
# SP/design-agent-cli-path.md section 1. ``dh-cli-usage`` must derive the plugin root from one of
# these -- never from a plugin-root variable, which only Claude Code resolves.
SKILL_DIR_TAGS = (
    "<skill_dir>${CLAUDE_SKILL_DIR}</skill_dir>",
    "<skill_dir>${KIMI_SKILL_DIR}</skill_dir>",
    "<skill_dir>${HERMES_SKILL_DIR}</skill_dir>",
)
ALLOWED_SKILL_DIR_VARIABLES = frozenset({"CLAUDE_SKILL_DIR", "KIMI_SKILL_DIR", "HERMES_SKILL_DIR"})
SAM_CLI_COMMAND = 'uv run "<plugin_root/>/sam_schema/cli.py"'

# (file, substring of the matched line) -> reason the line is data describing the variable, not an
# invocation of it. Mirrors SKILL_PATH_CITATION_EXCEPTIONS: every entry states why the match is not
# this guard's defect, so an empty reason is never mistaken for an oversight the next editor deletes.
PLUGIN_ROOT_DATA_LINES: dict[tuple[Path, str], str] = {
    (SKILLS_DIR / "code-review-architecture" / "SKILL.md", "strip `${CLAUDE_SKILL_DIR}`"): (
        "This line states, as data, the two placeholder spellings a graph-builder's script-path "
        "resolution step must strip before resolving a target. It documents which variables to "
        "recognise, not itself invoking one -- rewriting it to `<plugin_root/>` would delete the "
        "literal spelling the step's own rule needs to name."
    ),
    (SKILLS_DIR / "code-review-architecture" / "SKILL.md", '"SessionStart": [{"hooks"'): (
        "This is a literal `hooks.json` command string quoted as the worked example for this "
        "skill's own hook-edge-extraction step, the same spelling a real hooks.json command "
        "already carries verbatim. The step's job is to detect and record this exact text as an "
        "edge target, not to invoke it."
    ),
}

DOCS_DIR = PLUGIN_ROOT / "docs"
# Subtrees section 5 carves out of the guide-relocation scan: a measurement record reports what a
# harness was observed doing at the time, and a plan document is written against a layout a later
# plan may supersede. Neither is a live pointer a reader follows today.
DOCS_SCAN_EXCLUDED_DIRS = (DOCS_DIR / "work-ledger" / "measurements", DOCS_DIR / "plans")
ROOT_NAMED_DOCS = (PLUGIN_ROOT / "AGENTS.md", PLUGIN_ROOT / "README.md", PLUGIN_ROOT / "ARCHITECTURE.md")
# The old guide's name and the old MCP connection check's docs/ path -- both retired once section 2
# and section 5 move their content under skills/dh-cli-usage/references/.
STALE_GUIDE_NAME_SUBSTRINGS = ("dh-cli-usage-guide", "docs/mcp-connection-check.md")


def agent_files() -> list[Path]:
    """Collect every agent definition in this plugin.

    Returns:
        Sorted list of ``agents/*.md`` paths.

    Raises:
        AssertionError: If the directory holds no agent definitions, which would make every scan
            below pass by scanning nothing.
    """
    files = sorted(AGENTS_DIR.glob("*.md"))
    assert files, f"{AGENTS_DIR.relative_to(PLUGIN_ROOT)} holds no agent definitions to scan."
    return files


def skill_files() -> list[Path]:
    """Collect every skill definition file in this plugin, recursively.

    A skill's own ``SKILL.md`` and everything under its ``references/`` sit at varying depths under
    ``skills/<name>/``, so the scan walks the whole subtree rather than one directory level.

    Returns:
        Sorted list of ``skills/**/*.md`` paths.

    Raises:
        AssertionError: If the directory holds no skill files, which would make the scan below pass
            by scanning nothing.
    """
    files = sorted(SKILLS_DIR.rglob("*.md"))
    assert files, f"{SKILLS_DIR.relative_to(PLUGIN_ROOT)} holds no skill files to scan."
    return files


def matching_lines(pattern: re.Pattern[str], paths: list[Path]) -> list[str]:
    """Find every line in *paths* matching *pattern*.

    Args:
        pattern: Compiled pattern applied line by line.
        paths: Files to scan.

    Returns:
        Formatted ``path:lineno — matched text`` strings, one per match.
    """
    return [
        f"  {path.relative_to(PLUGIN_ROOT)}:{lineno} — {match.group(0)}"
        for path in paths
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        for match in pattern.finditer(line)
    ]


def governed_files() -> list[Path]:
    """Agent and skill files this module's CLI-path and plugin-root guards apply to.

    Excludes everything under ``skills/dh-cli-usage/`` -- that skill is the one place these
    patterns are meant to appear: it derives ``<plugin_root/>`` from its own directory and defines
    ``<sam_cli/>``, so every other file is meant to point at it instead of re-deriving either value.

    Returns:
        Sorted list of agent and skill files outside ``skills/dh-cli-usage/``.
    """
    return sorted(path for path in agent_files() + skill_files() if not path.is_relative_to(DH_CLI_USAGE_DIR))


def plugin_root_variable_offenders(paths: list[Path]) -> list[str]:
    """Find every ``${...PLUGIN_ROOT}`` reference in *paths* not covered by an exception.

    Args:
        paths: Files to scan, line by line.

    Returns:
        Formatted ``path:lineno -- matched text`` strings, one per unexcused match.
    """
    offenders: list[str] = []
    for path in paths:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for match in PLUGIN_ROOT_VARIABLE_RE.finditer(line):
                excused = any(file == path and substring in line for file, substring in PLUGIN_ROOT_DATA_LINES)
                if not excused:
                    offenders.append(f"  {path.relative_to(PLUGIN_ROOT)}:{lineno} — {match.group(0)}")
    return offenders


def guide_relocation_scan_files() -> list[Path]:
    """Files ``test_cli_guide_lives_in_dh_cli_usage`` scans for the CLI guide's old name or path.

    Every markdown file this plugin ships to a reader: ``skills/``, ``agents/`` and ``docs/`` (minus
    the two subtrees section 5 exempts) plus the three named root documents. A measurement record
    reports what a harness was observed doing at the time, and a plan document is written against a
    layout a later plan may supersede -- neither is a live pointer a reader follows today, so both
    subtrees are left out.

    Returns:
        Sorted list of the markdown files in scope for the scan.
    """
    docs_files = [
        path
        for path in DOCS_DIR.rglob("*.md")
        if not any(path.is_relative_to(excluded) for excluded in DOCS_SCAN_EXCLUDED_DIRS)
    ]
    root_files = [path for path in ROOT_NAMED_DOCS if path.is_file()]
    return sorted(agent_files() + skill_files() + docs_files + root_files)


def test_no_agent_names_a_specific_repository() -> None:
    """No agent definition writes a repository owner and name into a command.

    An agent shipped with this plugin runs against whatever project installs it. A slug baked into
    the prompt makes it query the wrong project and present the result as the installing project's
    own history — a wrong answer that looks exactly like a right one.
    """
    offenders = matching_lines(REPO_SLUG_RE, agent_files())

    assert not offenders, (
        "An agent definition names a specific repository:\n"
        + "\n".join(offenders)
        + "\nResolve the repository through the configured backend — `backlog_list_merged_prs` "
        "needs no slug — or from `.dh/config.yaml`'s `gh.repo`, per docs/github-cli-conventions.md."
    )


def test_no_agent_or_skill_cites_a_skill_by_plugin_rooted_path() -> None:
    """No agent or skill definition cites a skill as ``plugins/<plugin>/skills/<name>/SKILL.md``.

    The path resolves only from a checkout laid out like this one. The skill name resolves in every
    harness that loads the plugin, which is the whole set of places these agents and skills run.
    One skill citing a sibling skill by path is the same checkout-binding defect as an agent doing
    it, so this scans ``skills/`` alongside ``agents/`` — minus the files in
    ``SKILL_PATH_CITATION_EXCEPTIONS``, where the matched text is not this citation.
    """
    scanned = [path for path in agent_files() + skill_files() if path not in SKILL_PATH_CITATION_EXCEPTIONS]
    offenders = matching_lines(SKILL_PATH_RE, scanned)

    assert not offenders, (
        "An agent or skill definition cites a skill by filesystem path:\n"
        + "\n".join(offenders)
        + "\nName the skill instead (e.g. `dh:execution`) and, if a specific part is meant, name "
        "its section in prose. See rules/markdown-file-references.md, Skill Activation References. "
        "If the match is not this citation, add it to SKILL_PATH_CITATION_EXCEPTIONS with the "
        "reason — never drop it silently by narrowing the scan."
    )


def test_skill_path_citation_exceptions_still_exist() -> None:
    """Every file named in ``SKILL_PATH_CITATION_EXCEPTIONS`` is still on disk.

    An exception excuses a specific file's content; once that file is renamed, moved, or deleted,
    the entry excuses nothing and is a stale line no one has a reason to revisit. This fails loudly
    instead of leaving the exception to rot silently.
    """
    missing = [str(path.relative_to(PLUGIN_ROOT)) for path in SKILL_PATH_CITATION_EXCEPTIONS if not path.is_file()]

    assert not missing, (
        "SKILL_PATH_CITATION_EXCEPTIONS names a file that no longer exists: "
        + ", ".join(missing)
        + ". Remove the stale entry — it no longer excuses anything, and the scan should cover "
        "whatever replaced the file."
    )


def chain_steps_named(path: Path) -> list[str]:
    """List which steps of the backend-resolution chain *path* names.

    Args:
        path: Agent definition to inspect.

    Returns:
        Sorted labels from :data:`CHAIN_STEP_MARKERS` whose pattern occurs in the file.
    """
    text = path.read_text(encoding="utf-8")
    return sorted(label for label, pattern in CHAIN_STEP_MARKERS.items() if pattern.search(text))


def test_no_agent_derives_the_backend_chain_inline() -> None:
    """No agent definition carries the backend-resolution procedure, as shell or as prose.

    The chain has one definition and one agent-facing procedure: ``dh:backend-resolution``, which
    an agent loads through its ``skills:`` frontmatter. A copy in an agent file is banned by
    ``rules/shared-process-extraction.md`` whatever medium it is written in — a restatement in
    prose is the same two-copies-free-to-drift defect as a duplicated shell block, in a form that
    is harder to grep for. It is also how the original bug read: every inline re-derivation found
    so far implemented a prefix of the chain and stopped, which does not fail loudly. It returns a
    different backend than the rest of the plugin is using, and the agent then reports that
    backend's answer as the project's.
    """
    shell = [line for pattern in BACKEND_DERIVATION_PATTERNS for line in matching_lines(pattern, agent_files())]

    prose = [
        f"  {path.relative_to(PLUGIN_ROOT)} — names {len(steps)} steps of the chain: {', '.join(steps)}"
        for path in agent_files()
        if len(steps := chain_steps_named(path)) >= CHAIN_ENUMERATION_THRESHOLD
    ]

    assert not shell + prose, (
        "An agent definition re-derives the backend chain inline:\n"
        + "\n".join(sorted(shell) + sorted(prose))
        + "\nDelete it and load `dh:backend-resolution` through the agent's `skills:` frontmatter, "
        "the way `dh:subagent-contract` is loaded. The agent keeps what is specific to its own "
        "assignment and restates no part of the shared procedure — a summary is a copy that has "
        "already begun to drift. See rules/shared-process-extraction.md."
    )


def test_alignment_analyst_emits_one_distinct_verdict_per_assessment_value() -> None:
    """The three emitted verdict lines carry three different tokens.

    This is the reintroduction guard. Reusing one token across two outcomes is what made a skipped
    check indistinguishable from a divergence finding, and no downstream consumer would have
    caught it: nothing gates on this line.
    """
    text = ALIGNMENT_ANALYST.read_text(encoding="utf-8")
    emitted = EMITTED_VERDICT_RE.findall(text)

    assert len(emitted) == len(ASSESSMENT_VALUES), (
        f"{ALIGNMENT_ANALYST.relative_to(PLUGIN_ROOT)} emits {len(emitted)} verdict lines "
        f"({sorted(emitted)}) for {len(ASSESSMENT_VALUES)} assessment values "
        f"({sorted(ASSESSMENT_VALUES)}). Each value needs its own leading line."
    )
    assert len(set(emitted)) == len(emitted), (
        f"{ALIGNMENT_ANALYST.relative_to(PLUGIN_ROOT)} emits the same verdict token for more "
        f"than one outcome: {sorted(emitted)}. A repeated token makes 'I did not check' and "
        "'I checked and found something' arrive as the same signal."
    )


def test_alignment_analyst_keeps_the_verdict_tokens_this_module_guards() -> None:
    """The agent still spells its verdicts with the tokens named here.

    Without this, ``VERDICT_TOKENS`` is a claim about a file nothing rereads, and a rename could
    quietly leave the distinctness test guarding a set no longer in use.
    """
    present = set(ANY_VERDICT_RE.findall(ALIGNMENT_ANALYST.read_text(encoding="utf-8")))
    missing = sorted(VERDICT_TOKENS - present)

    assert not missing, (
        f"{ALIGNMENT_ANALYST.relative_to(PLUGIN_ROOT)} no longer uses {missing}. If a token was "
        "renamed, rename it here too; if MISSION_UNASSESSED is gone, the unassessed case is being "
        "reported as a finding again."
    )


def test_alignment_analyst_report_offers_every_assessment_value_finalize_accepts() -> None:
    """The report format still offers all three values the grooming validation gate accepts.

    ``groom/finalize.md`` matches the ``Alignment assessment:`` field literally and requires one of
    ALIGNED, DIVERGENT or NOT_APPLICABLE. Dropping a value from the producer's template leaves the
    gate accepting a value nothing writes.
    """
    text = ALIGNMENT_ANALYST.read_text(encoding="utf-8")
    field_line = next((line for line in text.splitlines() if line.startswith(ASSESSMENT_FIELD)), None)

    assert field_line is not None, (
        f"{ALIGNMENT_ANALYST.relative_to(PLUGIN_ROOT)} no longer shows an `{ASSESSMENT_FIELD}` "
        "line in its report template. That is the field groom/finalize.md validates."
    )
    unoffered = sorted(value for value in ASSESSMENT_VALUES if value not in field_line)

    assert not unoffered, (
        f"The report template no longer offers {unoffered}, which groom/finalize.md still accepts "
        f"for `{ASSESSMENT_FIELD}`."
    )


def test_no_agent_or_skill_names_a_plugin_root_variable() -> None:
    """No agent or skill definition writes a ``${...PLUGIN_ROOT}`` variable, outside ``dh-cli-usage``.

    Only Claude Code substitutes this template variable in a skill or agent body
    (SP/design-agent-cli-path.md section 0); every other measured harness ships it to the model as
    literal text. A file that names it directly re-derives what ``dh:dh-cli-usage`` exists to
    resolve once, from its own skill directory -- the checkout-binding defect this module already
    guards for a plugin-rooted skill path, in a second shape.
    """
    offenders = plugin_root_variable_offenders(governed_files())

    assert not offenders, (
        "An agent or skill definition names a plugin-root variable directly:\n"
        + "\n".join(offenders)
        + "\nWrite `<sam_cli/>` or `<plugin_root/>/…` and point at `dh:dh-cli-usage`, which resolves "
        "the plugin root from its own skill directory. If the match is data describing the "
        "variable rather than an invocation of it, add it to PLUGIN_ROOT_DATA_LINES with the reason."
    )


def test_plugin_root_data_line_exceptions_still_match() -> None:
    """Every ``PLUGIN_ROOT_DATA_LINES`` exception still names a real line in its file.

    Mirrors ``test_skill_path_citation_exceptions_still_exist``: an exception whose file is gone or
    whose substring no longer appears on any line excuses nothing, and is a stale entry the next
    editor has no reason to revisit.
    """
    stale = [
        f"{file.relative_to(PLUGIN_ROOT)} — {substring!r} not found in any line"
        for file, substring in PLUGIN_ROOT_DATA_LINES
        if not file.is_file() or not any(substring in line for line in file.read_text(encoding="utf-8").splitlines())
    ]

    assert not stale, (
        "PLUGIN_ROOT_DATA_LINES names an exception that no longer matches a line on disk:\n"
        + "\n".join(stale)
        + "\nRemove the stale entry — it no longer excuses anything."
    )


def test_no_agent_or_skill_runs_the_cli_by_path() -> None:
    """No agent or skill runs the CLI by its literal ``/sam_schema/cli.py`` path, outside ``dh-cli-usage``.

    Every caller is meant to write ``<sam_cli/>`` and let ``dh:dh-cli-usage`` resolve it from the
    plugin root it derives from its own directory. A file naming the path directly duplicates the
    one command string this move exists to stop duplicating (SP/design-agent-cli-path.md section 0,
    point 3).
    """
    offenders = matching_lines(PREFIXED_CLI_PATH_RE, governed_files())

    assert not offenders, (
        "An agent or skill definition names the CLI's literal path:\n"
        + "\n".join(offenders)
        + "\nWrite `<sam_cli/>` instead — `dh:dh-cli-usage` resolves it from its own skill "
        "directory, so no other file needs to know the CLI's location."
    )


def test_no_agent_links_a_relative_path() -> None:
    """No agent definition holds a markdown link with a relative target.

    An agent file has no filesystem location once shipped -- it is prompt text loaded by name, not
    read from a path a relative link could resolve against. The two matches on the current tree
    (``agents/task-worker.md``, ``agents/backlog-item-groomer.md``) are F3.
    """
    offenders = matching_lines(AGENT_RELATIVE_LINK_RE, agent_files())

    assert not offenders, (
        "An agent definition links a relative path:\n"
        + "\n".join(offenders)
        + "\nName the skill or agent instead (e.g. `dh:work-milestone`) — see "
        "rules/markdown-file-references.md."
    )


def test_every_agent_running_the_cli_preloads_dh_cli_usage() -> None:
    """Every agent whose body runs the CLI lists ``dh:dh-cli-usage`` in its ``skills:`` frontmatter.

    A dispatched agent starts with an empty conversation, so preload through frontmatter is the only
    deterministic way it reaches the skill that resolves ``<sam_cli/>`` before it needs to run a
    command. Matching the pre-move ``sam_schema/cli.py`` path too, alongside the post-move
    ``<sam_cli/>`` tag, keeps this guard from passing vacuously before any file is edited: on the
    current tree it is the old path that puts every offending agent into the matched set.
    """
    running: list[Path] = []
    missing: list[str] = []
    for path in agent_files():
        meta, body = _load_frontmatter_from_path(path)
        if not CLI_INVOCATION_RE.search(body):
            continue
        running.append(path)
        skills = _normalize_skills(meta.get("skills"))
        if DH_CLI_USAGE_SKILL_URI not in skills:
            missing.append(f"  {path.relative_to(PLUGIN_ROOT)} — skills: {skills}")

    assert running, "No agent's body runs the CLI; the preload guard below would pass vacuously."
    assert not missing, (
        "An agent runs the CLI without preloading the skill that resolves it:\n"
        + "\n".join(missing)
        + f"\nAdd `- {DH_CLI_USAGE_SKILL_URI}` to its `skills:` frontmatter."
    )


def test_dh_cli_usage_resolves_only_through_skill_dir_tags() -> None:
    """``dh-cli-usage``'s SKILL.md derives the plugin root from its own directory, no other way.

    Per SP/design-agent-cli-path.md section 3, the skill finds only its own directory (one
    ``<skill_dir>`` tag per harness that substitutes one) and derives ``<plugin_root/>`` as that
    directory's grandparent -- it names no plugin-root variable, because only Claude Code resolves
    one.
    """
    assert DH_CLI_USAGE.is_file(), (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} does not exist. Scaffold it with "
        "plugin-creator:skill-creator's init_skill.py, then write the section 3 body."
    )
    text = DH_CLI_USAGE.read_text(encoding="utf-8")

    missing_tags = [tag for tag in SKILL_DIR_TAGS if tag not in text]
    assert not missing_tags, f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} is missing skill-dir tag(s): {missing_tags}"

    unknown_variables = sorted(set(TEMPLATE_VARIABLE_RE.findall(text)) - ALLOWED_SKILL_DIR_VARIABLES)
    assert not unknown_variables, (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} names template variable(s) other than the three "
        f"skill-dir forms: {unknown_variables}"
    )

    assert "PLUGIN_ROOT" not in text, (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} names PLUGIN_ROOT; it must derive the plugin root "
        "only from its own skill directory, never from a plugin-root variable."
    )
    assert "<plugin_root>" not in text, (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} opens a `<plugin_root>` tag; `<plugin_root/>` is a "
        "derived, self-closing name, not a variable with a value tag."
    )
    assert SAM_CLI_COMMAND in text, (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} does not hold the `<sam_cli>` definition: {SAM_CLI_COMMAND!r}"
    )


def test_cli_guide_lives_in_dh_cli_usage() -> None:
    """The CLI guide and the MCP connection check live under ``dh-cli-usage``, and nowhere else names them.

    Section 2 and section 5 move ``dh-cli-usage-guide.md`` to
    ``dh-cli-usage/references/command-reference.md`` and ``docs/mcp-connection-check.md`` to
    ``dh-cli-usage/references/mcp-connection-check.md`` -- a runtime skill's reference material has
    one home, and nothing outside it should still point at either file's old name or old path once
    the move lands.
    """
    command_reference = DH_CLI_USAGE_DIR / "references" / "command-reference.md"
    connection_check = DH_CLI_USAGE_DIR / "references" / "mcp-connection-check.md"

    missing = [
        str(path.relative_to(PLUGIN_ROOT)) for path in (command_reference, connection_check) if not path.is_file()
    ]
    assert not missing, (
        "dh-cli-usage is missing its moved reference file(s): "
        + ", ".join(missing)
        + ". git mv the CLI guide and the MCP connection check into skills/dh-cli-usage/references/, "
        "per section 2 and section 5."
    )

    offenders = [
        f"  {path.relative_to(PLUGIN_ROOT)}:{lineno} — names {name!r}"
        for path in guide_relocation_scan_files()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        for name in STALE_GUIDE_NAME_SUBSTRINGS
        if name in line
    ]
    assert not offenders, (
        "A file still names the old CLI guide location:\n"
        + "\n".join(offenders)
        + "\nRepoint it at skills/dh-cli-usage/references/command-reference.md, or at the MCP "
        "connection check `dh:dh-cli-usage` now holds, per section 2 and section 5."
    )
