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
