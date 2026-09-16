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
  its own directory -- one ``<sam_cli>``/``<dh_scripts>`` block per harness's own skill-directory
  variable, each holding one full command line the caller appends arguments to. A raw template
  variable in an agent or skill body is the
  same checkout-binding defect as the plugin-rooted skill path above -- a substitution Claude Code
  performs that no other measured harness does -- so it is guarded the same way: a static scan
  with a named-reason exception table, not a runtime check. A skill may still write
  ``${CLAUDE_SKILL_DIR}`` bare, to reach its own files; only a ``SKILL_DIR/..`` parent-directory
  climb outside ``dh-cli-usage`` re-derives what that skill exists to resolve once, so only that
  shape is banned elsewhere. See ``CLAIMS-REGISTER.md``'s ``${CLAUDE_PLUGIN_ROOT}`` entry for what
  is measured, and ``rules/runtime-vs-design-time.md`` for why: a path or variable in runtime text
  must resolve in every environment the artifact can execute in, not just the one it was authored
  in. The guide these agents and skills pointed readers at moves with it, from
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

import json
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


# --- Plugin-root variable, skill-dir climb, and hard-coded CLI path (W2, dh-cli-usage) ----------
#
# ``dh:dh-cli-usage`` is the one place that derives the plugin root and the CLI's location. Every
# other agent and skill file is meant to say ``<sam_cli/>`` or ``<dh_scripts/>`` and point at that
# skill, never re-derive either value itself. These patterns are the three ways a file did that
# derivation directly instead: a raw ``${...PLUGIN_ROOT}`` template variable, a
# ``${...SKILL_DIR}/..`` parent-directory climb written out longhand, and the CLI's literal path.
# Only Claude Code substitutes a plugin-root or skill-dir template variable in a skill or agent
# body; every other measured harness ships one to the model as raw text, so a reference or doc
# file carrying it ships broken text everywhere else (``CLAIMS-REGISTER.md``'s
# ``${CLAUDE_PLUGIN_ROOT}`` entry; ``rules/runtime-vs-design-time.md``). ``dh-cli-usage`` instead
# derives the root from the skill's own directory, which every measured harness except Cursor gives
# the model.
PLUGIN_ROOT_VARIABLE_RE = re.compile(r"\$\{?[A-Z_]*PLUGIN_ROOT\b")
SKILL_DIR_PARENT_RE = re.compile(r"\$\{?[A-Z_]*SKILL_DIR\}?/\.\.")
CLI_PATH_RE = re.compile(r"sam_schema[/\\.]cli\b|run_sam_cli\.py")
CLI_TOKEN_RE = re.compile(r"<sam_cli\s*/>|<dh_scripts\s*/>")
# Unanchored: a definition written mid-line, inside prose or an HTML comment, is the same
# local-redefinition defect as one that opens a line -- inline code is stripped before this
# pattern runs, so a bare mention such as `<sam_cli>` in backticks does not count.
DEFINITION_TAG_RE = re.compile(r"<(?:sam_cli|mcp_server_scripts|dh_scripts|plugin_root)\b(?!\s*/>)")

# Checked separately from DEFINITION_TAG_RE: only a genuine block-opening line counts here, so an
# inline mention such as `<sam_cli>` in prose does not inflate the open-tag count the way an
# unanchored scan would.
BLOCK_OPEN_RE = re.compile(r"^\s*<(sam_cli|dh_scripts)\b(?!\s*/>)", re.MULTILINE)
NAMES_DH_CLI_USAGE_RE = re.compile(r"dh-cli-usage(?!-guide)")
TEMPLATE_VARIABLE_RE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)")
FENCED_BLOCK_RE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")

# The three link-target extraction shapes: an inline/reference-style markdown link target, a
# reference-style link *definition* (``[label]: target``), and an HTML ``href``/``src`` attribute.
LINK_TARGET_RES = (
    re.compile(r"\]\(\s*<?([^)>\s]+)"),
    re.compile(r"^\s*\[[^\]]+\]:\s*<?(\S+?)>?\s*$", re.MULTILINE),
    re.compile(r"(?:href|src)=[\"']([^\"']+)"),
)
# A target this module allows: an absolute URL scheme (``https:``, ``mailto:``, …) or an
# in-document anchor (``#section``). Anything else is a path the shipped agent file cannot resolve
# once it is loaded by name rather than read from disk (rules/markdown-file-references.md, Skill
# Activation References). ``file:`` is excluded from the scheme match: it still names a local
# path, just with a URI prefix in front of it.
ALLOWED_LINK_TARGET_RE = re.compile(r"^(?:(?!file:)[a-z][a-z0-9+.-]*:|#)")
# A bare path fragment naming this plugin's own tree: a ``./``/``../`` prefix, or a ``skills/``,
# ``agents/`` or ``references/`` segment. Requires that prefix or a named top-level directory so it
# does not fire on prose that merely uses the word "skills" (rules/markdown-file-references.md,
# Skill Activation References).
PLUGIN_INTERNAL_PATH_RE = re.compile(r"(?<![\w/])(?:\.\.?/|(?:skills|agents|references)/)[\w{}.-]+")

# A plugin-rooted path buried past the top level -- e.g. naming a `references/` file two levels
# into another skill's tree -- that PLUGIN_INTERNAL_PATH_RE's lookbehind cannot see, because the
# character just before its own `skills/`/`references/` segment is itself a path character.
# Requires the `plugins/<name>/` prefix, so it does not fire on the bare `skills/…` shape
# PLUGIN_INTERNAL_PATH_RE already covers.
PLUGIN_ROOTED_PATH_RE = re.compile(r"(?<![\w/.-])plugins/[\w.-]+/")

# Files excused from PLUGIN_ROOTED_PATH_RE entirely, each with why the matched text is data, not a
# citation to fix -- mirrors SKILL_PATH_CITATION_EXCEPTIONS.
AGENT_PATH_DATA_LINES: dict[Path, str] = {
    AGENTS_DIR / "plan-validator.md": (
        "The Example issue block states, as data, a literal Impact Radius entry an earlier stage "
        "wrote -- the finding's own description names the file a sync task missed. Rewriting it "
        "to a skill name would delete the path the worked example exists to show being reported "
        "back."
    )
}

DH_CLI_USAGE_DIR = SKILLS_DIR / "dh-cli-usage"
DH_CLI_USAGE = DH_CLI_USAGE_DIR / "SKILL.md"
DH_CLI_USAGE_SKILL_URI = "dh:dh-cli-usage"

FIRST_CLASS_HARNESSES = ("Claude Code", "Codex", "OpenCode", "Cursor")
SKILL_DIR_VARIABLES = ("CLAUDE_SKILL_DIR", "KIMI_SKILL_DIR", "HERMES_SKILL_DIR")
SKILL_ROOT_LINES = tuple(f"${{{variable}}}" for variable in SKILL_DIR_VARIABLES)
SAM_CLI_LINES = ('uv run "<skill-root>/../../sam_schema/cli.py"',)
DH_SCRIPTS_LINES = ("<skill-root>/../../scripts",)

# (file, substring of the matched line) -> reason the line is data describing the variable, not an
# invocation of it. Mirrors SKILL_PATH_CITATION_EXCEPTIONS: every entry states why the match is not
# this guard's defect, so an empty reason is never mistaken for an oversight the next person deletes.
PLUGIN_ROOT_DATA_LINES: dict[tuple[Path, str], str] = {
    (SKILLS_DIR / "code-review-architecture" / "SKILL.md", "`${CLAUDE_PLUGIN_ROOT}` placeholders"): (
        "This line states, as data, the two placeholder spellings a graph-builder's script-path "
        "resolution step must strip before resolving a target. It documents which variables to "
        "recognise, not itself invoking one -- rewriting it to `<sam_cli/>` would delete the "
        "literal spelling the step's own rule needs to name. The key spans the actual "
        "`${CLAUDE_PLUGIN_ROOT}` mention, not just the neighbouring `${CLAUDE_SKILL_DIR}` text, so "
        "a real invocation appended to the same line is not excused by proximity alone."
    ),
    (
        SKILLS_DIR / "code-review-architecture" / "SKILL.md",
        r'"SessionStart": [{"hooks": [{"command": "node \"${CLAUDE_PLUGIN_ROOT}',
    ): (
        "This is a literal `hooks.json` command string quoted as the worked example for this "
        "skill's own hook-edge-extraction step. The key stops right after the `PLUGIN_ROOT}` "
        "token and does not reach into the script filename that follows it, so the exception "
        "still matches if that filename is ever renamed, and it spans the actual variable mention "
        "rather than an unrelated prefix."
    ),
}

# The old guide's name and the old MCP connection check's docs/ path -- both retired once their
# content moves under skills/dh-cli-usage/references/.
STALE_GUIDE_NAME_SUBSTRINGS = ("dh-cli-usage-guide", "docs/mcp-connection-check.md")
# Subtrees the guide-relocation scan skips: a measurement record reports what a harness was
# observed doing at the time, a plan document is written against a layout a later plan may
# supersede, and a test/venv/generated-graph tree is not shipped prompt text. None of these is a
# live pointer a reader follows today.
GUIDE_RELOCATION_SCAN_EXCLUDED_PREFIXES = ("docs/work-ledger/measurements", "tests", ".venv", "graphify-out")


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

    Excludes only ``skills/dh-cli-usage/SKILL.md`` -- that file is the one place these patterns
    are meant to appear: it derives ``<plugin_root/>`` from its own directory and defines
    ``<sam_cli/>``, so every other file is meant to point at it instead of re-deriving either
    value. Its ``references/`` files stay governed and must use the tokens like everything else --
    the CLI guide and the MCP connection check that land there are exactly the files that used to
    carry the old plugin-root text, so excluding the whole subtree would have stopped checking
    them the moment they moved in. Hook scripts and ``hooks.json`` never
    enter this scan either: they are code the harness runs, not text the model reads, so
    ``agent_files()`` and ``skill_files()`` never walk ``hooks/`` in the first place.

    Returns:
        Sorted list of agent and skill files, excluding dh-cli-usage's own ``SKILL.md``.
    """
    return sorted(path for path in agent_files() + skill_files() if path != DH_CLI_USAGE)


def plugin_root_variable_offenders(paths: list[Path]) -> list[str]:
    """Find every ``${...PLUGIN_ROOT}`` reference in *paths* not covered by an exception.

    An exception excuses a match only when its position falls inside the exception's own
    substring span on that line -- a key present anywhere on the line used to excuse every match
    on it, so a real invocation appended after a legitimate data line would have been excused by
    proximity alone.

    Args:
        paths: Files to scan, line by line.

    Returns:
        Formatted ``path:lineno -- matched text`` strings, one per unexcused match.
    """
    offenders: list[str] = []
    for path in paths:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for match in PLUGIN_ROOT_VARIABLE_RE.finditer(line):
                excused = False
                for file, substring in PLUGIN_ROOT_DATA_LINES:
                    if file != path:
                        continue
                    start = line.find(substring)
                    if start != -1 and start <= match.start() < start + len(substring):
                        excused = True
                        break
                if not excused:
                    offenders.append(f"  {path.relative_to(PLUGIN_ROOT)}:{lineno} — {match.group(0)}")
    return offenders


def guide_relocation_scan_files() -> list[Path]:
    """Files ``test_cli_guide_and_connection_check_live_in_dh_cli_usage`` scans for the old CLI
    guide name or the old MCP connection check path.

    Every markdown file this plugin ships, from the plugin root down, minus the subtrees
    ``GUIDE_RELOCATION_SCAN_EXCLUDED_PREFIXES`` names and any path with a dot-prefixed directory
    part such as ``.claude-plugin`` (revision-4 row 4, m9) -- neither is prompt text a reader
    follows.

    Returns:
        Sorted list of the markdown files in scope for the scan.
    """
    return sorted(
        path
        for path in PLUGIN_ROOT.rglob("*.md")
        if not str(path.relative_to(PLUGIN_ROOT)).startswith(GUIDE_RELOCATION_SCAN_EXCLUDED_PREFIXES)
        and not any(part.startswith(".") for part in path.relative_to(PLUGIN_ROOT).parts)
    )


def _skill_body_for_uri(skill_uri: str) -> str:
    """Read the ``SKILL.md`` body a ``dh:<name>`` frontmatter reference preloads.

    Args:
        skill_uri: A single entry from an agent's normalised ``skills:`` list, e.g.
            ``"dh:execution"``.

    Returns:
        The file's text, or an empty string when *skill_uri* names no local ``dh:`` skill --
        either because it points at a different plugin, or because the skill directory is missing.
    """
    name = skill_uri.removeprefix("dh:")
    if name == skill_uri:
        return ""
    skill_path = SKILLS_DIR / name / "SKILL.md"
    return skill_path.read_text(encoding="utf-8") if skill_path.is_file() else ""


def _extract_tag_block(text: str, tag: str) -> list[list[str]]:
    """Return the stripped, non-empty line contents of every ``<tag>...</tag>`` block in *text*.

    Args:
        text: File text with fenced code blocks and HTML comments already stripped.
        tag: Element name, e.g. ``"sam_cli"``.

    Returns:
        One list of stripped lines per matched block, in document order.
    """
    pattern = re.compile(rf"<{tag}>(.*?)</{tag}>", re.DOTALL)
    return [
        [line.strip() for line in match.group(1).strip("\n").splitlines() if line.strip()]
        for match in pattern.finditer(text)
    ]


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
    """No governed file names a plugin-root variable, or climbs out of its skill directory by hand.

    Only Claude Code substitutes a ``${...PLUGIN_ROOT}`` template variable in a skill or agent
    body; every other measured harness ships it to the model as literal text. A file that names one
    directly re-derives what ``dh:dh-cli-usage`` exists to resolve once, from its own skill
    directory -- the checkout-binding defect this module already guards for a plugin-rooted skill
    path, in a second shape. Writing ``${...SKILL_DIR}/..`` longhand is the same re-derivation in a
    different spelling, so it is banned in every governed file except
    ``skills/dh-cli-usage/SKILL.md`` -- the one place that climb is meant to appear: the skill finds
    only its own directory and derives everything else from it.
    """
    root_offenders = plugin_root_variable_offenders(governed_files())
    skill_dir_offenders = matching_lines(SKILL_DIR_PARENT_RE, governed_files())
    offenders = root_offenders + skill_dir_offenders

    assert not offenders, (
        "An agent or skill definition names a plugin-root variable, or climbs out of a skill "
        "directory directly:\n"
        + "\n".join(offenders)
        + "\nWrite `<sam_cli/>` or `<dh_scripts/>` and point at `dh:dh-cli-usage`, which resolves "
        "both from its own skill directory. If the match is data describing the variable rather "
        "than an invocation of it, add it to PLUGIN_ROOT_DATA_LINES with the reason."
    )


def test_plugin_root_data_line_exceptions_still_match() -> None:
    """Every ``PLUGIN_ROOT_DATA_LINES`` exception still names a real, matching line with a reason.

    Mirrors ``test_skill_path_citation_exceptions_still_exist``: an exception whose file is gone,
    whose substring no longer appears on a line that actually matches ``PLUGIN_ROOT_VARIABLE_RE``,
    or whose reason is blank excuses nothing — a stale or reasonless entry is a line the next editor
    has no way to tell from an oversight.
    """
    stale: list[str] = []
    for (file, substring), reason in PLUGIN_ROOT_DATA_LINES.items():
        if not reason.strip():
            stale.append(f"{file.relative_to(PLUGIN_ROOT)} — {substring!r} has an empty reason")
            continue
        if not file.is_file():
            stale.append(f"{file.relative_to(PLUGIN_ROOT)} — {substring!r} — file does not exist")
            continue
        lines = file.read_text(encoding="utf-8").splitlines()
        if not any(substring in line and PLUGIN_ROOT_VARIABLE_RE.search(line) for line in lines):
            stale.append(f"{file.relative_to(PLUGIN_ROOT)} — {substring!r} not found on a plugin-root-variable line")

    assert not stale, (
        "PLUGIN_ROOT_DATA_LINES names an exception that no longer matches a real line:\n"
        + "\n".join(stale)
        + "\nRemove the stale entry — it no longer excuses anything."
    )


def test_no_agent_or_skill_runs_the_cli_by_path() -> None:
    """No agent or skill runs the CLI by its literal path, outside ``dh-cli-usage``.

    Every caller is meant to write ``<sam_cli/>`` and let ``dh:dh-cli-usage`` resolve it from the
    plugin root it derives from its own directory. This matches every shape a file named the CLI's
    location directly: a path prefixed with ``${CLAUDE_PLUGIN_ROOT}`` or a skill directory, a bare
    ``sam_schema/cli.py`` or ``sam_schema.cli`` module path, and ``scripts/run_sam_cli.py``, the MCP
    entry point's own script — duplicating the one command string this move exists to stop
    duplicating.
    """
    offenders = matching_lines(CLI_PATH_RE, governed_files())

    assert not offenders, (
        "An agent or skill definition names the CLI's literal path:\n"
        + "\n".join(offenders)
        + "\nWrite `<sam_cli/>` instead — `dh:dh-cli-usage` resolves it from its own skill "
        "directory, so no other file needs to know the CLI's location."
    )


def test_no_agent_links_a_relative_path() -> None:
    """No agent definition links, or bare-names, a path into this plugin's own tree.

    An agent file has no filesystem location once shipped -- it is prompt text loaded by name, not
    read from a path a relative link could resolve against. Three scans catch the three ways this
    showed up: a markdown or HTML link whose target is neither an absolute URL scheme nor an
    in-document anchor, a bare ``./``, ``../``, ``skills/…``, ``agents/…`` or ``references/…``
    path fragment anywhere in the file, fenced code included, and a ``plugins/<name>/…`` path
    buried past the top level that the second scan's lookbehind cannot see because the character
    just before its own ``skills/``/``references/`` segment is itself a path character
    All three need the ``./``/``../`` prefix, a named top-level directory, or the ``plugins/``
    prefix, so none of them fire on prose that merely uses the word "skills" -- and
    the link scan catches reference-style link definitions and HTML attributes too, not just an
    inline ``](...)`` target. The two matches on the current tree (``agents/task-worker.md``,
    ``agents/backlog-item-groomer.md``) are F3. ``AGENT_PATH_DATA_LINES`` excuses a file from the
    third scan entirely, each entry with the reason the matched text is data, not a citation to fix.
    """
    link_offenders: list[str] = []
    for path in agent_files():
        text = INLINE_CODE_RE.sub("", FENCED_BLOCK_RE.sub("", path.read_text(encoding="utf-8")))
        for pattern in LINK_TARGET_RES:
            link_offenders.extend(
                f"  {path.relative_to(PLUGIN_ROOT)} — link target {target!r}"
                for target in pattern.findall(text)
                if not ALLOWED_LINK_TARGET_RE.match(target)
            )

    path_offenders = matching_lines(PLUGIN_INTERNAL_PATH_RE, agent_files())
    rooted_scanned = [path for path in agent_files() if path not in AGENT_PATH_DATA_LINES]
    rooted_offenders = matching_lines(PLUGIN_ROOTED_PATH_RE, rooted_scanned)

    offenders = link_offenders + path_offenders + rooted_offenders
    assert not offenders, (
        "An agent definition links or names a relative filesystem path:\n"
        + "\n".join(offenders)
        + "\nName the skill or agent instead (e.g. `dh:work-milestone`) — see "
        "rules/markdown-file-references.md. If the match is data rather than a citation to fix, "
        "add it to AGENT_PATH_DATA_LINES with the reason."
    )


def test_agent_path_data_line_exceptions_still_exist() -> None:
    """Every file named in ``AGENT_PATH_DATA_LINES`` is still on disk, with a non-empty reason.

    Mirrors ``test_skill_path_citation_exceptions_still_exist``: an exception whose file is gone
    excuses nothing, and is a stale line no one has a reason to revisit.
    """
    stale = [
        str(path.relative_to(PLUGIN_ROOT))
        for path, reason in AGENT_PATH_DATA_LINES.items()
        if not path.is_file() or not reason.strip()
    ]

    assert not stale, (
        "AGENT_PATH_DATA_LINES names a stale entry (missing file or empty reason): "
        + ", ".join(stale)
        + ". Remove it — it no longer excuses anything, and the scan should cover whatever "
        "replaced the file."
    )


def test_every_agent_running_the_cli_preloads_dh_cli_usage() -> None:
    """Every agent that reaches the CLI, directly or through a preloaded skill, preloads
    ``dh:dh-cli-usage`` and can run a Bash command.

    A dispatched agent starts with an empty conversation, so preload through frontmatter is the
    only deterministic way it reaches the skill that resolves ``<sam_cli/>`` before it needs to run
    a command. "Reaches the CLI" means the union of the agent's own body and the ``SKILL.md`` of
    every ``dh:`` skill in its ``skills:`` list -- an agent that only inherits the CLI through
    ``dh:subagent-contract``'s work-ledger block still needs the preload. Every agent this matches
    must also carry a tool whose name is exactly ``Bash`` in ``tools:``, or omit ``tools:`` entirely
    -- a substring check would also accept an unrelated tool merely containing the word, such as
    ``BashOutput``, which gives no way to start a process. A ``dh:`` skill URI that names no local
    skill directory -- a typo, or a skill that was renamed or deleted -- silently drops its
    contribution to the union instead of being flagged, which would let an agent that only reaches
    the CLI through a misspelled preload escape this check entirely; that URI is reported as its
    own reason. A file whose text opens with ``---`` but whose
    frontmatter fails to parse is a silent false negative for this whole check: it would read back
    as "no skills: declared" and never get flagged, so that case fails loudly instead.
    """
    running: list[Path] = []
    missing: list[str] = []
    for path in agent_files():
        meta, body = _load_frontmatter_from_path(path)
        text = path.read_text(encoding="utf-8")
        assert meta or not text.lstrip().startswith("---"), (
            f"{path.relative_to(PLUGIN_ROOT)}: frontmatter did not parse"
        )

        skills = _normalize_skills(meta.get("skills"))
        unresolved = [
            uri
            for uri in skills
            if uri.startswith("dh:") and not (SKILLS_DIR / uri.removeprefix("dh:") / "SKILL.md").is_file()
        ]
        union = body + "".join(_skill_body_for_uri(uri) for uri in skills)
        if not (CLI_TOKEN_RE.search(union) or CLI_PATH_RE.search(union)) and not unresolved:
            continue
        running.append(path)

        reasons: list[str] = []
        if DH_CLI_USAGE_SKILL_URI not in skills:
            reasons.append(f"skills: {skills} has no `dh:dh-cli-usage`")
        tools = meta.get("tools")
        tool_names = tools if isinstance(tools, list) else str(tools).split(",")
        if tools is not None and "Bash" not in {str(name).strip().split("(", 1)[0] for name in tool_names}:
            reasons.append(f"tools: {tools!r} has no `Bash`")
        if unresolved:
            reasons.append(f"skills: {unresolved} name no local dh skill")
        if reasons:
            missing.append(f"  {path.relative_to(PLUGIN_ROOT)} — {'; '.join(reasons)}")

    assert running, "No agent reaches the CLI; the preload guard below would pass vacuously."
    assert not missing, (
        "An agent reaches the CLI without preloading the skill that resolves it, without a way to "
        "run the resulting command, or through a skills: entry naming no local dh skill:\n"
        + "\n".join(missing)
        + f"\nAdd `- {DH_CLI_USAGE_SKILL_URI}` to its `skills:` frontmatter, make sure `tools:` "
        "either lists `Bash` or is absent, and fix any misspelled `dh:` skill reference."
    )


def test_dh_cli_usage_resolves_through_every_first_class_harness_skill_root() -> None:
    """``dh-cli-usage``'s SKILL.md derives ``<sam_cli/>`` and ``<dh_scripts/>`` only from its own
    directory, and states its documented failure path.

    The command definitions use one model-resolved skill-root token, and the instructions support
    both harness-supplied root metadata and the three known body-substitution variables.
    """
    assert DH_CLI_USAGE.is_file(), (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} does not exist. Scaffold it with "
        "plugin-creator:skill-creator's init_skill.py, then write its <sam_cli>/<dh_scripts> body."
    )
    raw = DH_CLI_USAGE.read_text(encoding="utf-8")
    stripped = HTML_COMMENT_RE.sub("", FENCED_BLOCK_RE.sub("", raw))

    skill_root_blocks = _extract_tag_block(stripped, "skill_root")
    assert skill_root_blocks == [list(SKILL_ROOT_LINES)]

    sam_cli_blocks = _extract_tag_block(stripped, "sam_cli")
    assert len(sam_cli_blocks) == 1, (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} holds {len(sam_cli_blocks)} closed <sam_cli> "
        "block(s); expected exactly one."
    )
    assert tuple(sam_cli_blocks[0]) == SAM_CLI_LINES, (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)}'s <sam_cli> block is {sam_cli_blocks[0]!r}, "
        f"expected {list(SAM_CLI_LINES)!r}."
    )

    dh_scripts_blocks = _extract_tag_block(stripped, "dh_scripts")
    assert len(dh_scripts_blocks) == 1, (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} holds {len(dh_scripts_blocks)} closed <dh_scripts> "
        "block(s); expected exactly one."
    )
    assert tuple(dh_scripts_blocks[0]) == DH_SCRIPTS_LINES, (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)}'s <dh_scripts> block is {dh_scripts_blocks[0]!r}, "
        f"expected {list(DH_SCRIPTS_LINES)!r}."
    )

    missing_harnesses = [harness for harness in FIRST_CLASS_HARNESSES if harness not in raw]
    assert not missing_harnesses, f"dh-cli-usage does not explain skill-root resolution for {missing_harnesses}"
    unknown_variables = sorted(set(TEMPLATE_VARIABLE_RE.findall(raw)) - set(SKILL_DIR_VARIABLES))
    assert not unknown_variables, f"dh-cli-usage names unknown template variables: {unknown_variables}"

    assert "PLUGIN_ROOT" not in raw, (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} names PLUGIN_ROOT; it must derive the plugin root "
        "only from its own skill directory, never from a plugin-root variable."
    )
    assert "<plugin_root" not in raw, (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} opens a `<plugin_root` tag; that token is retired "
        "in favor of `<sam_cli/>` and `<dh_scripts/>`."
    )
    assert "plan --help" in stripped, (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} does not name the `plan --help` probe outside a "
        "fenced block or HTML comment."
    )
    assert "STATUS: BLOCKED" in stripped, (
        f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} does not instruct `STATUS: BLOCKED` on failure "
        "outside a fenced block or HTML comment."
    )
    for harness in ("Codex", "OpenCode", "Cursor"):
        assert harness in stripped, f"dh-cli-usage does not name its {harness} fallback."


def test_implementation_manager_does_not_execute_an_unresolved_cli_token() -> None:
    """Skill load-time injection cannot execute the prose-only ``<sam_cli/>`` token."""
    implementation_manager = SKILLS_DIR / "implementation-manager" / "SKILL.md"
    injection_lines = [
        line
        for line in implementation_manager.read_text(encoding="utf-8").splitlines()
        if line.startswith("!") and "<sam_cli/>" in line
    ]
    assert not injection_lines


def test_work_ledger_docs_describe_mcp_ledger_routing() -> None:
    """The runner docs must not deny the imported-plan MCP route implemented by the server."""
    for relative in ("docs/work-ledger/work-loop.md", "docs/work-ledger/runner-contract.md"):
        text = (PLUGIN_ROOT / relative).read_text(encoding="utf-8")
        assert "server_ledger_routing.py" in text
        assert "MCP remains available" in text
        assert "CLI is the only path to" not in text


def test_impact_analyst_description_fits_frontmatter_limit() -> None:
    """Agent discovery metadata must fit the portable 1024-character description limit."""
    frontmatter, _ = _load_frontmatter_from_path(AGENTS_DIR / "impact-analyst.md")
    assert len(str(frontmatter["description"])) <= 1024


def test_cli_tokens_are_not_executed_before_model_resolution() -> None:
    """Dynamic context executes before instruction tokens can be resolved by the model."""
    implementation_manager = (SKILLS_DIR / "implementation-manager" / "SKILL.md").read_text(encoding="utf-8")
    dynamic_cli_lines = [
        line for line in implementation_manager.splitlines() if line.startswith("!`") and "<sam_cli" in line
    ]

    assert not dynamic_cli_lines, f"Dynamic commands execute unresolved CLI tokens: {dynamic_cli_lines}"


def test_context_refinement_splits_the_resolved_cli_command_for_subprocess() -> None:
    """The safe argv example must not pass a complete CLI command as one executable argument."""
    context_refinement = (AGENTS_DIR / "context-refinement.md").read_text(encoding="utf-8")

    assert 'shlex.split("<sam_cli/>")' in context_refinement
    assert '["uv", "run", "<sam_cli/>"' not in context_refinement


def test_mcp_connection_check_names_both_server_commands() -> None:
    """Manual recovery must provide runnable commands for both shipped MCP servers."""
    connection_check = (DH_CLI_USAGE_DIR / "references" / "mcp-connection-check.md").read_text(encoding="utf-8")

    assert 'uv run --script "<dh_scripts/>/run_backlog_server.py"' in connection_check
    assert 'uv run --script "<dh_scripts/>/run_sam_server.py"' in connection_check
    assert "<mcp_server_scripts" not in connection_check


def test_cli_guide_and_connection_check_live_in_dh_cli_usage() -> None:
    """The CLI command reference and the MCP connection check live under ``dh-cli-usage``, and
    nowhere else still names either by its old name or old path, and dh-cli-usage links both.

    ``dh-cli-usage-guide.md`` moves to ``dh-cli-usage/references/command-reference.md`` and
    ``docs/mcp-connection-check.md`` moves to ``dh-cli-usage/references/mcp-connection-check.md`` --
    a runtime skill's reference material has one home. Four failure shapes, gathered into one
    assertion so a later failure is never hidden behind an earlier one: the new files are missing,
    the old files are still on disk, ``dh-cli-usage/SKILL.md`` does not link one or both of them, or
    some other shipped markdown file still names the old location.
    """
    command_reference = DH_CLI_USAGE_DIR / "references" / "command-reference.md"
    connection_check = DH_CLI_USAGE_DIR / "references" / "mcp-connection-check.md"
    old_guide = SKILLS_DIR / "dh-meta-docs" / "references" / "dh-cli-usage-guide.md"
    old_connection_check = PLUGIN_ROOT / "docs" / "mcp-connection-check.md"

    missing = [
        str(path.relative_to(PLUGIN_ROOT)) for path in (command_reference, connection_check) if not path.is_file()
    ]
    still_present = [str(path.relative_to(PLUGIN_ROOT)) for path in (old_guide, old_connection_check) if path.is_file()]

    dh_cli_usage_text = DH_CLI_USAGE.read_text(encoding="utf-8") if DH_CLI_USAGE.is_file() else ""
    missing_links = [
        link
        for link in ("](./references/command-reference.md)", "](./references/mcp-connection-check.md)")
        if link not in dh_cli_usage_text
    ]

    offenders = [
        f"  {path.relative_to(PLUGIN_ROOT)}:{lineno} — names {name!r}"
        for path in guide_relocation_scan_files()
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1)
        for name in STALE_GUIDE_NAME_SUBSTRINGS
        if name in line
    ]

    problems: list[str] = []
    if missing:
        problems.append("missing moved reference file(s): " + ", ".join(missing))
    if still_present:
        problems.append("old CLI reference location(s) still on disk: " + ", ".join(still_present))
    if missing_links:
        problems.append(
            f"{DH_CLI_USAGE.relative_to(PLUGIN_ROOT)} is missing the reference link(s): " + ", ".join(missing_links)
        )
    if offenders:
        problems.append("file(s) still name the old CLI reference location:\n" + "\n".join(offenders))

    assert not problems, (
        "dh-cli-usage's reference relocation is incomplete:\n"
        + "\n\n".join(problems)
        + "\ngit mv the CLI guide and the MCP connection check into skills/dh-cli-usage/references/, "
        "add both reference links to dh-cli-usage/SKILL.md, and repoint every remaining referrer at "
        "dh-cli-usage instead of the old location."
    )


def test_every_file_using_the_cli_token_names_dh_cli_usage() -> None:
    """Every governed file that writes ``<sam_cli/>`` or ``<dh_scripts/>`` names ``dh-cli-usage``
    at or before the first line that does.

    The token alone tells a reader nothing about where it resolves. A caller that writes it without
    pointing at ``dh:dh-cli-usage`` first -- the reference pointer every caller is meant to carry --
    ships a tag with no activation instruction attached to it, or one that arrives too late to have
    been read before the token is used. HTML comments are stripped before either line is located,
    so a name mentioned only in a comment does not count. This cannot see a dh command written
    without the token at all (a bare ``plan read --address …``);
    the skill's own body, not this test, covers that form.
    """
    offenders: list[str] = []
    for path in governed_files():
        lines = HTML_COMMENT_RE.sub("", path.read_text(encoding="utf-8")).splitlines()
        token_line = next((i for i, line in enumerate(lines) if CLI_TOKEN_RE.search(line)), None)
        if token_line is None:
            continue
        name_line = next((i for i, line in enumerate(lines) if NAMES_DH_CLI_USAGE_RE.search(line)), None)
        if name_line is None or name_line > token_line:
            offenders.append(f"  {path.relative_to(PLUGIN_ROOT)}")

    assert not offenders, (
        "A file writes `<sam_cli/>` or `<dh_scripts/>` without naming dh-cli-usage at or before it:\n"
        + "\n".join(offenders)
        + "\nAdd the reference pointer, naming `dh:dh-cli-usage`, before the file's first use of "
        "`<sam_cli/>` or `<dh_scripts/>`."
    )


def cli_definition_tag_offenders(paths: list[Path]) -> list[str]:
    """Find every ``DEFINITION_TAG_RE`` match in *paths*, anywhere on a line, inline code excluded.

    Inline code spans are stripped first, so prose that merely names the tag in backticks -- e.g.
    a `` `<sam_cli>` `` mention -- does not count; a definition written mid-line outside code, such
    as inside prose or an HTML comment, still does.

    Args:
        paths: Files to scan, line by line.

    Returns:
        Formatted ``path:lineno -- matched text`` strings, one per match.
    """
    offenders: list[str] = []
    for path in paths:
        text = INLINE_CODE_RE.sub("", path.read_text(encoding="utf-8"))
        for lineno, line in enumerate(text.splitlines(), start=1):
            offenders.extend(
                f"  {path.relative_to(PLUGIN_ROOT)}:{lineno} — {match.group(0)}"
                for match in DEFINITION_TAG_RE.finditer(line)
            )
    return offenders


def test_cli_definition_blocks_live_only_in_dh_cli_usage() -> None:
    """No governed file opens a ``<sam_cli>``, ``<mcp_server_scripts>``, ``<dh_scripts>`` or
    ``<plugin_root>`` definition block, on its own line or mid-line.

    ``dh:dh-cli-usage`` is the one place these are defined; every other file is meant to reference
    them as self-closing tags (``<sam_cli/>``, ``<dh_scripts/>``) and point at that skill instead of
    opening its own copy. The negative lookahead also catches a ``<plugin_root path=…>`` opening
    tag, the retired token's own local-definition shape.
    """
    offenders = cli_definition_tag_offenders(governed_files())

    assert not offenders, (
        "A file opens a local CLI definition block:\n"
        + "\n".join(offenders)
        + "\nDelete it and reference `dh:dh-cli-usage` instead -- it is the one place these blocks "
        "are defined."
    )


def test_manifests_keep_the_default_skills_path() -> None:
    """Every dh install manifest keeps the default ``./skills/`` layout the skill-directory design
    assumes.

    Section 1's "``../..`` from the skill directory is the dh root" column depends on every install
    target giving the model a skill directory two levels under the plugin root — exactly what the
    default ``skills/`` layout produces. A manifest that points ``skills`` somewhere else would
    break that assumption silently, with nothing else in this plugin catching it.
    """
    codex_manifest = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
    claude_manifest = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    cursor_manifest = PLUGIN_ROOT / ".cursor-plugin" / "plugin.json"

    codex_skills = json.loads(codex_manifest.read_text(encoding="utf-8")).get("skills")
    assert codex_skills == "./skills/", (
        f"{codex_manifest.relative_to(PLUGIN_ROOT)} sets `skills` to {codex_skills!r}, not the default './skills/'."
    )

    for manifest in (claude_manifest, cursor_manifest):
        skills_value = json.loads(manifest.read_text(encoding="utf-8")).get("skills")
        assert skills_value in (None, "./skills/"), (
            f"{manifest.relative_to(PLUGIN_ROOT)} sets `skills` to {skills_value!r}; expected it "
            "absent (default) or './skills/'."
        )

    nested = [str(p.relative_to(PLUGIN_ROOT)) for p in SKILLS_DIR.glob("**/SKILL.md") if p.parent.parent != SKILLS_DIR]
    assert not nested, (
        "A skill sits deeper than skills/<name>/SKILL.md, breaking the '../.. is the dh root' "
        f"assumption dh-cli-usage's own derivation depends on: {nested}"
    )
