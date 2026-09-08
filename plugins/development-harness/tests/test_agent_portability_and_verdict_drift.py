"""Guards agent definitions against re-binding to one checkout, and the alignment verdict set.

An agent definition in ``agents/`` is prompt text shipped to whatever repository installs this
plugin. Anything in it that names *this* checkout — a repository slug, a path that only resolves
from this directory layout — is correct here and wrong everywhere else, and nothing about running
it here reveals that. The two shapes guarded below are the ones that were actually found:

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

The third guard is a producer contract rather than a portability one. ``alignment-analyst`` used to
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


def test_no_agent_cites_a_skill_by_plugin_rooted_path() -> None:
    """No agent definition cites a skill as ``plugins/<plugin>/skills/<name>/SKILL.md``.

    The path resolves only from a checkout laid out like this one. The skill name resolves in every
    harness that loads the plugin, which is the whole set of places these agents run.
    """
    offenders = matching_lines(SKILL_PATH_RE, agent_files())

    assert not offenders, (
        "An agent definition cites a skill by filesystem path:\n"
        + "\n".join(offenders)
        + "\nName the skill instead (e.g. `dh:execution`) and, if a specific part is meant, name "
        "its section in prose. See rules/markdown-file-references.md, Skill Activation References."
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
