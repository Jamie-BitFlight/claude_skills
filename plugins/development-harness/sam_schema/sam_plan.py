"""Grouped Typer commands for ``sam plan``, over the two stores the ledger migration spans.

Two surfaces answer on this group at once. ``dh_core.ledger_spec.COMMANDS`` names the work
ledger's commands and the flags each one takes, and every command it names offers those flags.
The commands that existed before the ledger keep every flag and behaviour they had, on the
pre-ledger ``ContentTaskProvider`` path, because the plugin's skills call them that way today and
the slice that rewrites those skills has not run. A command both surfaces name offers the union of
the two flag sets and chooses a store per invocation.

Which store a command uses, in order:

1. A flag only the pre-ledger command had — every name in :data:`LEGACY_FLAGS`, such as
   ``--plan-dir``, ``--search``, ``--context`` or ``--priority`` — selects the content store.
2. A flag only ``ledger_spec`` names — ``--attempt``, ``--set``, ``--conflict-group``,
   ``--base-sha`` and the rest — selects the ledger.
3. Flags from both is an error rather than a precedence rule: the two name different stores, so an
   invocation that carries both has asked for two answers and gets neither.
4. With neither, a command that names a plan uses the store that holds that plan: the ledger when
   its database already exists and carries that plan id, and the content store otherwise. The
   database is never created to answer the question, so a content-store command on a repository
   with no ledger touches nothing of the ledger's.
5. With neither and no plan named, the store that command passes :func:`store_for` as its
   ``default``. ``create`` and ``list`` take no plan address at all; ``validate`` and ``status``
   reach this rule too, when their optional address is absent. Only ``create`` overrides the
   ``default`` parameter, so every other command that lands on rule 5 reads the ledger.

``create`` defaults to the content store, so no pre-ledger write moves: ``plan create --slug S
--goal G`` still writes a content record and still prints ``plan_id``, which is what the plugin's
skills call today and what ``tests_sam/test_cli_provider_addresses.py``'s
``test_create_persists_opaque_owner_reference`` reads back. A caller that means the ledger says so
with a ledger-only flag — ``--base-sha`` or ``--quality-gate`` — as ``tests_sam/scripted_runner.py``'s
``LoopDriver.build_plan`` does; every later command in that loop then names the plan, so rule 4 keeps it on
the ledger. A misrouted write is the one routing mistake asking again does not undo, which is why
``create`` is the command that keeps its old default rather than taking the new one.

``list`` defaults to the ledger, because ``ledger_spec`` gives ``list`` no flags of its own: a
ledger default is the only way its rows can be read at all, and reading the wrong store prints the
other store's rows rather than writing anything. This is the one place a pre-ledger caller's
behaviour moves. Naming the content store keeps the old path and the old output — ``--search``,
``--offset``, ``--limit``, ``--filter`` or ``--plan-dir`` is each enough. Every other pre-ledger
invocation reaches the content store exactly as it did, because it either carries one of those
flags or names a plan the ledger does not hold.

The legacy branch goes when Slice 6 of ``docs/work-ledger/plan.md`` retires the content record as
a store: :data:`LEGACY_FLAGS`, :func:`store_for` and every function below marked as the content
path are deleted with it, leaving one command per ``ledger_spec.COMMANDS`` entry.

:func:`check_surface` compares the group against the specification at import, in both directions
and flag by flag, so a command or a flag added to the specification is a loud failure here rather
than a surface that quietly lacks it; the union is expressed by :data:`LEGACY_FLAGS`, so a legacy
flag that outlives its command is loud too.

What a ledger command prints follows ``ledger_spec.REASONS``. A refusal writes its reason code to
stderr and exits non-zero; a no-op writes its reason code to stdout and exits zero; anything else
writes the result as compact JSON. ``dispatch`` is the one exception: it prints the new attempt
number and nothing else, because that number is the runner key every later command passes back as
``--attempt``.

``ledger_spec.RETIRED_COMMANDS`` names the commands a later slice deletes. They stand here
unchanged, on the pre-ledger path and with no routing, because skills still call them.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal, NoReturn

import dh_paths
import typer
from backlog_core.backend_protocol import get_config, require_github_extras
from backlog_core.backend_types import ContentProvider
from backlog_core.models import (
    BacklogError,
    ContentProviderError,
    GitHubUnavailableError,
    Output,
    UnsupportedBackendCapabilityError,
    get_repo_root,
)
from dh_core import ledger, ledger_spec, operations
from github import GithubException
from pydantic import TypeAdapter, ValidationError
from ruamel.yaml import YAML, YAMLError
from typer.main import get_command

from sam_schema import cli_output
from sam_schema.cli_inputs import (
    AppendTaskInput,
    CreatePlanInput,
    PlanUpdateFields,
    PlanUpdateInput,
    TaskUpdateFields,
    TaskUpdateInput,
)
from sam_schema.core.action_models import CreatePlanConfig, TaskDefinition, UpdatePlanConfig
from sam_schema.core.addressing import (
    AddressingError,
    parse_address,
    resolve_plan_address,
    resolve_provider_plan_address,
)
from sam_schema.core.backends.content import ContentTaskProvider
from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider, plan_id_from_path
from sam_schema.core.exceptions import BookendValidationError, PlanNotFoundError, TaskNotFoundError
from sam_schema.core.models import AcceptanceCriterion, Complexity, CreatePlanError, PlanState, Priority, TaskStatus
from sam_schema.readers.detect import FormatDetectionError
from sam_schema.writers.yaml_writer import write_plan

_PLAN_LOAD_ERRORS: tuple[type[Exception], ...] = (
    FileNotFoundError,
    FormatDetectionError,
    ValueError,
    TypeError,
    PlanNotFoundError,
)
_YAML_FRONTMATTER_PARTS = 3
_ACCEPTANCE_CRITERIA_ADAPTER = TypeAdapter(list[AcceptanceCriterion])

_SYNC_ERRORS: tuple[type[Exception], ...]
try:
    from backlog_core.operations import sync_items as _sync_backlog

    _BACKLOG_CORE_AVAILABLE = True
    _SYNC_ERRORS = (BacklogError, OSError, ValueError)
except ImportError:
    _BACKLOG_CORE_AVAILABLE = False
    _SYNC_ERRORS = (OSError, ValueError)

MILESTONE_ERRORS: tuple[type[Exception], ...] = (
    UnsupportedBackendCapabilityError,
    GitHubUnavailableError,
    BacklogError,
    GithubException,
)
"""What the GitHub read behind ``from-milestone`` raises when it cannot answer."""

LEDGER_ERRORS: tuple[type[Exception], ...] = (LookupError, ValueError, ContentProviderError)
"""What a ledger call raises for an address that names nothing, or an argument it rejects.

``ContentProviderError`` is here for ``export``: the projection store is the configured backend's
content capability, so a backend without one, or a record the target refuses to write, surfaces as
that error rather than as a refusal. Without it the CLI answers a configuration problem with a
traceback instead of the message-and-exit every other failure here gets.

A refusal is not one of these: it carries a ``ledger_spec.REASONS`` code and is caught separately,
because its code is the whole message and the exit is the surface's contract rather than an error
string a caller reads.
"""

GIT_TIMEOUT_SECONDS = 30
"""How long ``git rev-parse`` may take to name a branch head."""

ACCEPTANCE_FIELD = "acceptance_criteria"
VERIFICATION_FIELD = "verification_steps"
GROOMED_FIELDS: tuple[str, ...] = (ACCEPTANCE_FIELD, VERIFICATION_FIELD)
"""The two task columns ``from-milestone`` fills from an issue's groomed sections."""

app = typer.Typer(name="plan", help="SAM plan and task operations.", no_args_is_help=True, rich_markup_mode=None)


def _plan_dir(value: Path | None) -> Path:
    return dh_paths.plan_dir() if value is None else value


def _error(message: str, code: int = 1) -> NoReturn:
    cli_output.err(message, code)


def _emit(value: object) -> None:
    cli_output.output_json(value)


def _address(value: str, backend: ContentTaskProvider | None = None) -> tuple[str, str | None]:
    try:
        if backend is not None:
            return resolve_provider_plan_address(value, backend)
        plan_ref, task_ref = parse_address(value)
    except (AddressingError, ValueError) as exc:
        _error(str(exc))
        raise AssertionError from exc
    raw_plan, _, _ = value.partition("/")
    raw_plan = raw_plan.strip()
    if re.fullmatch(r"P[0-9a-f]{8}", raw_plan, re.IGNORECASE):
        return raw_plan, task_ref
    return plan_ref, task_ref


def _backend() -> ContentTaskProvider:
    provider = get_config().backend
    if not isinstance(provider, ContentProvider):
        _error("Active backend does not support plan content")
    return ContentTaskProvider(provider)


# ---------------------------------------------------------------------------
# Choosing a store: the union of the two flag sets, and the rule between them
# ---------------------------------------------------------------------------


class Store(StrEnum):
    """The two stores a command of this group can read and write."""

    LEDGER = "ledger"
    """``dh_core.ledger``: the repository's SQLite work ledger."""

    CONTENT = "content"
    """``ContentTaskProvider`` over the configured backend's plan content records."""


LEGACY_FLAGS: dict[str, frozenset[str]] = {
    "create": frozenset({
        "--context",
        "--issue",
        "--task-id",
        "--task-title",
        "--task-status",
        "--task-agent",
        "--task-dependency",
        "--task-priority",
        "--task-complexity",
        "--plan-dir",
    }),
    "append-task": frozenset({
        "--task-status",
        "--task-agent",
        "--task-dependency",
        "--task-priority",
        "--task-complexity",
        "--stdin",
        "--plan-dir",
    }),
    "finalize": frozenset({"--plan-dir"}),
    "validate": frozenset({"--address", "--plan-dir"}),
    "list": frozenset({"--search", "--offset", "--limit", "--filter", "--plan-dir"}),
    "status": frozenset({"--all", "--plan-dir"}),
    "ready": frozenset({"--full", "--plan-dir"}),
    "update": frozenset({
        "--context",
        "--feature",
        "--version",
        "--description",
        "--state",
        "--goal",
        "--acceptance-criteria-structured-json",
        "--issue",
        "--owner-reference",
        "--autonomy",
        "--title",
        "--task-status",
        "--agent",
        "--priority",
        "--complexity",
        "--dependency",
        "--skill",
        "--completed",
        "--last-activity",
        "--plan-dir",
    }),
    "read": frozenset({"--plan-dir"}),
    "state": frozenset({"--plan-dir"}),
}
"""Per command, the flags the pre-ledger command had that ``ledger_spec`` does not name.

Each entry is the second half of that command's offered surface: :func:`check_surface` requires a
command to offer its specification flags and these and nothing else, so a flag that outlives the
command it belonged to is as loud as a missing one. Passing any of them selects
:data:`Store.CONTENT`. The whole table goes when Slice 6 retires the content store.
"""


def named(flags: Mapping[str, object]) -> list[str]:
    """Return the flags of *flags* the caller actually passed.

    A flag counts as passed when its value differs from what the parser leaves for an absent one:
    ``None`` for a value option, ``False`` for a switch, an empty list for a repeatable option, and
    ``0`` for ``--offset``, whose default is a number rather than ``None``.

    Args:
        flags: Flag name, with its leading dashes, to the value the parser produced.

    Returns:
        The names that were passed, in the order the mapping declares them.
    """
    absent: tuple[object, ...] = (None, False, 0, "", (), [])
    return [name for name, value in flags.items() if value not in absent]


def ledger_holds(plan: str) -> bool:
    """Answer whether the ledger already carries a plan, without creating one.

    The database is only opened when its file is already there, so asking the question on a
    repository that has no ledger writes nothing and leaves no database behind.

    Args:
        plan: The plan id as the caller wrote it.

    Returns:
        Whether the ledger holds a plan row with that id.
    """
    if not plan or not ledger.database_path().exists():
        return False
    conn = _open()
    try:
        return any(str(row.get("plan_id")) == plan for row in ledger.list_plans(conn))
    finally:
        conn.close()


def store_for(
    command: str,
    *,
    legacy: Mapping[str, object],
    spec: Mapping[str, object],
    plan: str | None = None,
    default: Store = Store.LEDGER,
) -> Store:
    """Choose the store one invocation of a command both surfaces name is asking for.

    The module docstring states the rule this implements.

    Args:
        command: The command name, for the message when the two flag sets are mixed.
        legacy: The command's ``LEGACY_FLAGS`` names to the values the parser produced.
        spec: The command's ledger-only flag names to the values the parser produced.
        plan: The plan id the invocation names, when it names one.
        default: The store to use when no flag and no plan names one, which is rule 5. Each
            caller that can reach rule 5 states its own, because the reason differs per command.

    Returns:
        The store to read and write.
    """
    from_legacy = named(legacy)
    from_spec = named(spec)
    if from_legacy and from_spec:
        _error(
            f"plan {command} was given {', '.join(from_legacy)} for the content store and "
            f"{', '.join(from_spec)} for the ledger; each names a different store, so pass one set or the other"
        )
    if from_legacy:
        return Store.CONTENT
    if from_spec:
        return Store.LEDGER
    if plan is not None:
        return Store.LEDGER if ledger_holds(plan) else Store.CONTENT
    return default


def raw_plan_of(address: str | None) -> str | None:
    """Read the plan id out of an address without resolving it against a store.

    Routing runs before a store is chosen, so it reads the address as written rather than through
    ``resolve_provider_plan_address``, which would reach the content store to answer.

    Args:
        address: A ``P`` or ``P/T`` address, or None.

    Returns:
        The plan id as written, or None when there is no address or no plan part.
    """
    if address is None:
        return None
    plan_ref, _, _ = address.partition("/")
    return plan_ref.strip() or None


# ---------------------------------------------------------------------------
# The ledger surface: what the specification says, and how a result is printed
# ---------------------------------------------------------------------------


def flag_values(command: str, flag: str) -> tuple[str, ...]:
    """Return the alternatives a ``ledger_spec`` flag's value description lists.

    ``--from content|legacy|dispatch`` is the shape; the alternatives are read from the
    specification rather than restated here, so adding one is a change in one place.

    Args:
        command: The ``ledger_spec.COMMANDS`` name.
        flag: The flag name, with its leading dashes.

    Returns:
        The alternatives, in the order the specification writes them.

    Raises:
        KeyError: When the specification has no such command or flag.
    """
    for entry in ledger_spec.COMMANDS:
        if entry.name != command:
            continue
        for declared in entry.flags:
            if declared.name == flag:
                return tuple(part.strip() for part in declared.value.split("|") if part.strip())
    msg = f"ledger_spec.COMMANDS has no {flag} on {command}"
    raise KeyError(msg)


IMPORT_SOURCES: dict[str, Callable[[], Any]] = {
    "content": _backend,
    "legacy": lambda: LocalYamlTaskProvider(dh_paths.plan_dir()),
}
"""Each ``import --from`` value that has a reader, and the task backend that reads it."""

UNREADY_IMPORT_SOURCES: dict[str, str] = {
    "dispatch": "Slice 5 moves the DISPATCH_PLAN reader under sam_schema/readers; import --from dispatch lands with it"
}
"""Each ``import --from`` value with no reader yet, and what would give it one."""

EXPORT_TARGETS: tuple[str, ...] = flag_values("export", "--to")
"""Every ``export --to`` value the specification names."""


def check_import_sources() -> None:
    """Reject an ``import --from`` vocabulary that does not match the specification's.

    Raises:
        ValueError: When the specification names a source this module neither reads nor records as
            unready, or this module names one the specification does not.
    """
    named_sources = set(flag_values("import", "--from"))
    covered = set(IMPORT_SOURCES) | set(UNREADY_IMPORT_SOURCES)
    parts: list[str] = []
    if named_sources - covered:
        parts.append(f"ledger_spec names import --from {', '.join(sorted(named_sources - covered))} with nothing here")
    if covered - named_sources:
        parts.append(
            f"this module names import --from {', '.join(sorted(covered - named_sources))}, which ledger_spec does not"
        )
    if parts:
        raise ValueError("; ".join(parts))


def check_groomed_fields() -> None:
    """Reject a groomed-section field that is not a task column.

    Raises:
        ValueError: When a name in :data:`GROOMED_FIELDS` is not in ``ledger_spec.TASK_MODEL_FIELDS``.
    """
    unknown = [name for name in GROOMED_FIELDS if name not in ledger_spec.TASK_MODEL_FIELDS]
    if unknown:
        msg = f"{', '.join(unknown)} are not in ledger_spec.TASK_MODEL_FIELDS"
        raise ValueError(msg)


def offered_options() -> dict[str, set[str]]:
    """Read the long options every command of the plan group actually offers.

    The options are read off the built command rather than off the annotations, so what this
    compares against the specification is the same surface ``--help`` prints. Reading the
    annotations instead would restate Typer's own rule that an ``Option`` inside ``Annotated``
    carries its first declaration in the ``default`` slot, and would go stale the day that changes.

    Returns:
        Command name to the long options it offers.
    """
    group = get_command(app)
    commands: dict[str, Any] = getattr(group, "commands", {})
    return {
        name: {option for parameter in command.params for option in parameter.opts if option.startswith("--")}
        for name, command in commands.items()
    }


def check_surface() -> None:
    """Reject a plan group that does not offer each specified command's flags and its legacy ones.

    Raises:
        ValueError: When the specification names a command this group lacks, when a command offers
            a different set of flags than the specification and :data:`LEGACY_FLAGS` give it, or
            when :data:`LEGACY_FLAGS` names a command the specification does not.
    """
    offered = offered_options()
    specified = {entry.name for entry in ledger_spec.COMMANDS}
    parts: list[str] = [
        f"LEGACY_FLAGS names {name}, which ledger_spec.COMMANDS does not"
        for name in sorted(set(LEGACY_FLAGS) - specified)
    ]
    for entry in ledger_spec.COMMANDS:
        if entry.name not in offered:
            parts.append(f"ledger_spec.COMMANDS names {entry.name} with no command in the plan group")
            continue
        expected = {flag.name for flag in entry.flags} | LEGACY_FLAGS.get(entry.name, frozenset())
        found = offered[entry.name]
        if expected != found:
            parts.append(
                f"{entry.name} offers {sorted(found)} where ledger_spec.COMMANDS and LEGACY_FLAGS "
                f"name {sorted(expected)}"
            )
    if parts:
        raise ValueError("; ".join(parts))


def _refused(reason: str) -> NoReturn:
    """Print a refusal's reason code on stderr and exit non-zero.

    Args:
        reason: A ``ledger_spec.REASONS`` code of kind ``REFUSAL``.

    Raises:
        typer.Exit: Always.
    """
    typer.echo(reason, err=True)
    raise typer.Exit(1)


def _noop(reason: str) -> NoReturn:
    """Print a no-op's reason code on stdout and exit zero.

    Args:
        reason: A ``ledger_spec.REASONS`` code of kind ``NOOP``.

    Raises:
        typer.Exit: Always.
    """
    typer.echo(reason)
    raise typer.Exit(0)


def _emit_transition(result: ledger.TransitionResult) -> None:
    """Print one transition's result, or the no-op reason it stopped on.

    Args:
        result: What the ledger returned.
    """
    if result.noop:
        _noop(result.noop)
    _emit(result)


def _open() -> sqlite3.Connection:
    """Open the repository's ledger, refusing the way a command refuses.

    Returns:
        An open connection with the schema present.
    """
    try:
        return ledger.open_ledger()
    except ledger.Refusal as exc:
        _refused(exc.reason)


@contextmanager
def _ledger() -> Iterator[sqlite3.Connection]:
    """Open the ledger for one command and close it however the command ends.

    A refusal raised inside the block leaves through :func:`_refused`, and an address that names
    nothing or an argument the ledger rejects leaves through :func:`_error`; both close the
    connection on the way out.

    Yields:
        An open connection.
    """
    conn = _open()
    try:
        yield conn
    except ledger.Refusal as exc:
        _refused(exc.reason)
    except LEDGER_ERRORS as exc:
        _error(str(exc))
    finally:
        conn.close()


def _plan_of(value: str) -> str:
    """Read the plan id out of a ``--plan-address``.

    Args:
        value: The address, which must name a plan and not a task.

    Returns:
        The plan id.
    """
    plan_ref, _, task_ref = value.partition("/")
    if task_ref.strip():
        _error("--plan-address must identify a plan, not a task")
    if not plan_ref.strip():
        _error("--plan-address must name a plan")
    return plan_ref.strip()


def _task_of(value: str) -> tuple[str, str]:
    """Split a ``--address`` into its plan and task ids.

    Args:
        value: The address, in ``P/T`` form.

    Returns:
        The plan id and the task id.
    """
    plan_ref, _, task_ref = value.partition("/")
    if not plan_ref.strip() or not task_ref.strip():
        _error(f"Address '{value}' must name a plan and a task, as P/T")
    task = task_ref.strip()
    return plan_ref.strip(), f"T{task}" if task.isdigit() else task


def _optional_task_of(value: str | None) -> tuple[str | None, str | None]:
    """Split an optional ``--address`` for the two commands a ``--path`` can address instead.

    Args:
        value: The address, or None.

    Returns:
        The plan id and the task id, or two Nones.
    """
    if value is None:
        return None, None
    return _task_of(value)


def _set_values(pairs: list[str] | None, columns: Sequence[str]) -> dict[str, Any]:
    """Decode ``--set field=value`` pairs into the mapping ``update`` takes.

    A value that parses as JSON is used as JSON, so a list, a number or a boolean reaches the
    column with its own type; anything else is the literal string.

    A name outside ``columns`` is refused here rather than dropped by the ledger: ``update``
    appends a ``fields`` event, and ``ledger_spec.COLUMNS`` says which columns that event's fold
    sets. ``tasks.status``, ``started``, ``completed`` and ``last_activity`` are not among them —
    each names the lifecycle events instead — so ``--set status=complete`` would otherwise report
    success while the task stayed where it was.

    Args:
        pairs: The raw ``field=value`` strings.
        columns: The columns the ``fields`` event sets, from ``ledger.TASK_FIELD_COLUMNS`` or
            ``ledger.PLAN_FIELD_COLUMNS``.

    Returns:
        Field name to value.
    """
    values: dict[str, Any] = {}
    for pair in pairs or []:
        name, separator, raw = pair.partition("=")
        if not separator or not name.strip():
            _error(f"--set expects 'field=value', got: {pair!r}")
        try:
            values[name.strip()] = json.loads(raw)
        except json.JSONDecodeError:
            values[name.strip()] = raw
    refused = sorted(set(values) - set(columns))
    if refused:
        _error(
            f"--set may not write {', '.join(refused)}: no fields event sets them in ledger_spec.COLUMNS. "
            "A task's status moves with dispatch, finish, state, reclaim or accept"
        )
    return values


def body_section(body: str, field: str) -> str:
    """Read one groomed markdown section out of an issue body.

    Args:
        body: The issue body.
        field: The task column the section fills; its heading is that name in title case.

    Returns:
        The section's text, or an empty string when the body carries no such heading.
    """
    heading = re.escape(field.replace("_", " ").title())
    pattern = re.compile(rf"^#{{1,6}}\s+{heading}\s*$(.*?)(?=^#{{1,6}}\s|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE)
    match = pattern.search(body)
    return match.group(1).strip() if match else ""


def branch_head(branch: str) -> str:
    """Name the commit an integration branch points at, which becomes the plan's base sha.

    Args:
        branch: The branch name.

    Returns:
        The full commit sha.
    """
    git = shutil.which("git")
    if git is None:
        _error("git is not on PATH, so --integration-branch cannot be resolved to a base sha")
    process = subprocess.run(
        [git, "rev-parse", "--verify", f"{branch}^{{commit}}"],
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
        cwd=get_repo_root(),
    )
    if process.returncode:
        _error(f"could not resolve --integration-branch {branch}: {process.stderr.strip()}")
    return process.stdout.strip()


def milestone_items(milestone_number: int) -> list[ledger.MilestoneItem]:
    """Read a milestone's open issues as the items ``from-milestone`` builds tasks from.

    ``depends_on`` is left empty. A milestone's issues carry no dependency field, and the
    dispatch-plan record that did carry one retires with Slice 5, which is where the reader that
    can supply it lands.

    Args:
        milestone_number: The milestone.

    Returns:
        One item per open issue, in the order the backend returned them.
    """
    try:
        extras = require_github_extras(get_config().backend, "from-milestone")
        gh_repo = extras.get_github("")
        owner, repo_name = gh_repo.full_name.split("/", 1)
        nodes = extras.sync_issues_graphql(gh_repo, owner, repo_name, state="OPEN", milestone_number=milestone_number)
    except MILESTONE_ERRORS as exc:
        _error(str(exc))
    return [
        ledger.MilestoneItem(
            issue=int(node["number"]),
            title=str(node["title"]),
            acceptance_criteria=body_section(node["body"] or "", ACCEPTANCE_FIELD),
            verification_steps=body_section(node["body"] or "", VERIFICATION_FIELD),
        )
        for node in nodes
    ]


def import_sources(source: str, plan_address: str | None, *, all_plans: bool) -> list[ledger.PlanSource]:
    """Read the plans one ``import`` invocation writes.

    Args:
        source: The ``--from`` value.
        plan_address: The one plan to read, when ``--all`` is absent.
        all_plans: Read every plan the source holds.

    Returns:
        One source per plan, ready for ``ledger.import_plan``.
    """
    if source in UNREADY_IMPORT_SOURCES:
        _error(f"--from {source} is not available yet: {UNREADY_IMPORT_SOURCES[source]}")
    if source not in IMPORT_SOURCES:
        _error(f"--from must be one of {', '.join(flag_values('import', '--from'))}, got: {source!r}")
    if all_plans == (plan_address is not None):
        _error("provide --plan-address or --all, not both and not neither")
    backend = IMPORT_SOURCES[source]()
    ids = (
        [summary.plan_id for summary in operations.list_plans(backend)] if all_plans else [_plan_of(str(plan_address))]
    )
    try:
        return [ledger.plan_source(operations.read_plan(backend, plan_id).plan, source=source) for plan_id in ids]
    except (*_PLAN_LOAD_ERRORS, OSError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)


# ---------------------------------------------------------------------------
# The content path: the pre-ledger helpers, unchanged, until Slice 6
# ---------------------------------------------------------------------------


def _task_options(
    task_id: str | None,
    title: str | None,
    status: TaskStatus | None,
    agent: str | None,
    dependencies: list[str] | None,
    priority: int | None,
    complexity: str | None,
) -> TaskDefinition | None:
    if task_id is None and title is None:
        return None
    if task_id is None or title is None:
        _error("--task-id and --task-title must be provided together")
    values: dict[str, object] = {"id": task_id, "title": title}
    if status is not None:
        values["status"] = status
    if agent is not None:
        values["agent"] = agent
    if dependencies is not None:
        values["dependencies"] = dependencies
    if priority is not None:
        values["priority"] = priority
    if complexity is not None:
        values["complexity"] = complexity
    try:
        return TaskDefinition.model_validate(values)
    except ValidationError as exc:
        _error(str(exc))
        raise AssertionError from exc


def _task_from_stdin() -> dict[str, object]:
    """Read a single task definition as a YAML mapping from stdin.

    Supports the full ``Task`` field set (body, description, acceptance
    criteria, verification steps, handoff, skills, etc.) that the scalar
    typed options in :func:`_task_options` do not expose. Callers must
    validate the returned mapping through ``TaskDefinition.model_validate``.

    Returns:
        Raw task mapping ready for ``TaskDefinition`` validation.
    """
    raw = sys.stdin.read()
    if not raw.strip():
        _error("stdin is empty — provide a YAML task mapping via --stdin")
    parsed = YAML(typ="safe").load(raw)
    if not isinstance(parsed, dict):
        _error("stdin must be a single YAML task mapping")
        raise TypeError(parsed)
    return parsed


def content_create(
    slug: str,
    goal: str,
    context: str | None,
    issue: int | None,
    owner_reference: str | None,
    task: TaskDefinition | None,
) -> None:
    """Create a plan in the content store, as the pre-ledger ``create`` did.

    Args:
        slug: The plan's feature slug.
        goal: The one-sentence goal statement.
        context: Shared context for every task.
        issue: The GitHub issue the plan serves.
        owner_reference: The opaque work item the plan record belongs to.
        task: The one task the typed options describe, when they describe one.
    """
    try:
        config = CreatePlanInput(
            slug=slug, goal=goal, tasks=[] if task is None else [task], context=context, issue=issue
        )
        action_config = CreatePlanConfig.model_validate({
            **config.to_config().model_dump(),
            "owner_reference": owner_reference,
        })
        backend = _backend()
        result = operations.create_plan(backend, **action_config.model_dump(exclude={"action"}))
    except (ValidationError, ValueError, OSError, BookendValidationError) as exc:
        _error(str(exc))
    if isinstance(result, CreatePlanError):
        _error(result.error, 2)
    _emit(result)


def content_update(
    plan_address: str,
    task_id: str | None,
    context: str | None,
    feature: str | None,
    version: str | None,
    description: str | None,
    state_value: PlanState | None,
    goal: str | None,
    acceptance_criteria_structured_json: str | None,
    issue: str | None,
    owner_reference: str | None,
    autonomy: Literal["full_auto", "checkpoint", "per_task"] | None,
    title: str | None,
    task_status: TaskStatus | None,
    agent: str | None,
    priority: Priority | None,
    complexity: Complexity | None,
    dependency: list[str] | None,
    skill: list[str] | None,
    append_section: str | None,
    section_content: str | None,
    completed: str | None,
    last_activity: str | None,
) -> None:
    """Update declared plan or task fields in the content store, as the pre-ledger ``update`` did.

    Args:
        plan_address: The plan, or a plan and task, to update.
        task_id: The task to target, when the address names only a plan.
        context: Shared plan context.
        feature: Plan feature name.
        version: Plan version.
        description: Plan description.
        state_value: Plan state.
        goal: Plan goal.
        acceptance_criteria_structured_json: Structured acceptance criteria, as compact JSON.
        issue: The issue the plan serves.
        owner_reference: The opaque work item the plan record belongs to.
        autonomy: The dispatch gating mode.
        title: Task title.
        task_status: Task status.
        agent: Task agent.
        priority: Task priority.
        complexity: Task complexity.
        dependency: Task dependencies.
        skill: Task skills.
        append_section: The markdown section to append to the task.
        section_content: The section's body.
        completed: The task's completion timestamp.
        last_activity: The task's last-activity timestamp.
    """
    backend = _backend()
    plan_ref, task_ref = _address(plan_address, backend)
    target_task = task_id or (f"T{task_ref}" if task_ref and task_ref.isdigit() else task_ref)
    if target_task:
        plan_fields = (
            feature,
            version,
            description,
            state_value,
            goal,
            acceptance_criteria_structured_json,
            issue,
            autonomy,
        )
        if any(v is not None for v in plan_fields):
            _error(
                "plan-level fields (--feature, --goal, --description, etc.) must not be combined with "
                "task-targeted updates (--task-id, or plan address with task ref)"
            )
        try:
            has_task_fields = any(
                value is not None
                for value in (
                    title,
                    task_status,
                    agent,
                    priority,
                    complexity,
                    dependency,
                    skill,
                    completed,
                    last_activity,
                )
            )
            fields = (
                TaskUpdateFields(
                    title=title,
                    status=task_status,
                    agent=agent,
                    priority=priority,
                    complexity=complexity,
                    dependencies=dependency,
                    skills=skill,
                    completed=completed,
                    last_activity=last_activity,
                )
                if has_task_fields
                else None
            )
            request = TaskUpdateInput(
                plan_address=plan_ref,
                task_id=target_task,
                fields=fields,
                append_section=append_section,
                section_content=section_content,
            )
            values = request.fields.as_operation_fields() if request.fields is not None else None
        except ValidationError as exc:
            _error(str(exc))
    else:
        plan_values = (
            feature,
            version,
            description,
            state_value,
            goal,
            context,
            acceptance_criteria_structured_json,
            issue,
            autonomy,
        )
        if (
            owner_reference is not None
            and not any(value is not None for value in plan_values)
            and append_section is None
            and section_content is None
        ):
            values = None
        else:
            try:
                plan_update_fields = PlanUpdateFields(
                    feature=feature,
                    version=version,
                    description=description,
                    state=state_value,
                    goal=goal,
                    context=context,
                    acceptance_criteria_structured=(
                        _ACCEPTANCE_CRITERIA_ADAPTER.validate_json(acceptance_criteria_structured_json)
                        if acceptance_criteria_structured_json is not None
                        else None
                    ),
                    issue=issue,
                    autonomy=autonomy,
                )
                plan_request = PlanUpdateInput(
                    plan_address=plan_ref,
                    fields=plan_update_fields,
                    append_section_name=append_section,
                    section_content=section_content,
                )
                values = plan_request.fields.as_operation_fields() if plan_request.fields else None
            except ValidationError as exc:
                _error(str(exc))
    try:
        action_config = UpdatePlanConfig(
            context=context,
            set_fields_json=values,
            task_id=target_task,
            append_section_name=append_section,
            section_content=section_content,
            owner_reference=owner_reference,
        )
        result = operations.update_plan_fields(
            backend,
            plan_ref,
            context=action_config.context,
            set_fields=action_config.set_fields_json,
            owner_reference=action_config.owner_reference,
            task_id=action_config.task_id,
            append_section_name=action_config.append_section_name,
            section_content=action_config.section_content,
        )
    except (
        ValidationError,
        ValueError,
        KeyError,
        FileNotFoundError,
        PlanNotFoundError,
        FormatDetectionError,
        BookendValidationError,
    ) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)
    _emit(result)


# ---------------------------------------------------------------------------
# Plan-scoped commands
# ---------------------------------------------------------------------------


@app.command("create")
def create(
    slug: Annotated[str, typer.Option("--slug")],
    goal: Annotated[str, typer.Option("--goal")],
    owner_reference: Annotated[str | None, typer.Option("--owner-reference")] = None,
    base_sha: Annotated[str | None, typer.Option("--base-sha")] = None,
    quality_gate: Annotated[list[str] | None, typer.Option("--quality-gate")] = None,
    context: Annotated[str | None, typer.Option("--context")] = None,
    issue: Annotated[int | None, typer.Option("--issue", min=1)] = None,
    task_id: Annotated[str | None, typer.Option("--task-id")] = None,
    task_title: Annotated[str | None, typer.Option("--task-title")] = None,
    task_status: Annotated[TaskStatus | None, typer.Option("--task-status")] = None,
    task_agent: Annotated[str | None, typer.Option("--task-agent")] = None,
    task_dependencies: Annotated[list[str] | None, typer.Option("--task-dependency")] = None,
    task_priority: Annotated[int | None, typer.Option("--task-priority", min=1, max=5)] = None,
    task_complexity: Annotated[Complexity | None, typer.Option("--task-complexity")] = None,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Create a drafting plan; tasks follow with append-task, or one comes from the typed options."""
    store = store_for(
        "create",
        legacy={
            "--context": context,
            "--issue": issue,
            "--task-id": task_id,
            "--task-title": task_title,
            "--task-status": task_status,
            "--task-agent": task_agent,
            "--task-dependency": task_dependencies,
            "--task-priority": task_priority,
            "--task-complexity": task_complexity,
            "--plan-dir": plan_dir,
        },
        spec={"--base-sha": base_sha, "--quality-gate": quality_gate},
        default=Store.CONTENT,
    )
    if store is Store.CONTENT:
        content_create(
            slug,
            goal,
            context,
            issue,
            owner_reference,
            _task_options(
                task_id, task_title, task_status, task_agent, task_dependencies, task_priority, task_complexity
            ),
        )
        return
    with _ledger() as conn:
        _emit_transition(
            ledger.create(
                conn,
                slug=slug,
                goal=goal,
                owner_reference=owner_reference,
                base_sha=base_sha,
                quality_gates=quality_gate,
            )
        )


@app.command("append-task")
def append_task(
    plan_address: Annotated[str, typer.Option("--plan-address")],
    task_id: Annotated[str | None, typer.Option("--task-id")] = None,
    task_title: Annotated[str | None, typer.Option("--task-title")] = None,
    conflict_group: Annotated[str | None, typer.Option("--conflict-group")] = None,
    task_status: Annotated[TaskStatus | None, typer.Option("--task-status")] = None,
    task_agent: Annotated[str | None, typer.Option("--task-agent")] = None,
    task_dependencies: Annotated[list[str] | None, typer.Option("--task-dependency")] = None,
    task_priority: Annotated[int | None, typer.Option("--task-priority", min=1, max=5)] = None,
    task_complexity: Annotated[Complexity | None, typer.Option("--task-complexity")] = None,
    stdin: Annotated[bool, typer.Option("--stdin", help="Read the full task definition as YAML from stdin")] = False,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Append one task to a drafting plan, from typed options or a YAML mapping on stdin.

    ``--stdin`` accepts the full ``Task`` field set (body, description, acceptance criteria,
    verification steps, handoff, skills, etc.) that the scalar typed options do not expose. It
    reaches the content store only, and cannot be combined with the scalar task options.
    """
    store = store_for(
        "append-task",
        legacy={
            "--task-status": task_status,
            "--task-agent": task_agent,
            "--task-dependency": task_dependencies,
            "--task-priority": task_priority,
            "--task-complexity": task_complexity,
            "--stdin": stdin,
            "--plan-dir": plan_dir,
        },
        spec={"--conflict-group": conflict_group},
        plan=raw_plan_of(plan_address),
    )
    if store is Store.LEDGER:
        if task_id is None or task_title is None:
            _error("--task-id and --task-title are required")
        with _ledger() as conn:
            _emit_transition(
                ledger.append_task(
                    conn, _plan_of(plan_address), task_id=task_id, task_title=task_title, conflict_group=conflict_group
                )
            )
        return
    backend = _backend()
    plan_ref, task_ref = _address(plan_address, backend)
    if task_ref is not None:
        _error("--plan-address must identify a plan, not a task")
    has_scalar_task_option = any(
        value is not None
        for value in (task_id, task_title, task_status, task_agent, task_dependencies, task_priority, task_complexity)
    )
    if stdin and has_scalar_task_option:
        _error("--stdin cannot be combined with typed task options")
    try:
        if stdin:
            task = TaskDefinition.model_validate(_task_from_stdin())
        else:
            task = _task_options(
                task_id, task_title, task_status, task_agent, task_dependencies, task_priority, task_complexity
            )
            if task is None:
                _error("--task-id and --task-title are required (or use --stdin)")
        config = AppendTaskInput(plan_address=plan_ref, task=task)
        result = operations.append_task(backend, plan_ref, config.task)
    except (
        ValidationError,
        ValueError,
        PlanNotFoundError,
        FileNotFoundError,
        FormatDetectionError,
        BookendValidationError,
    ) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)
    _emit(result)


@app.command("finalize")
def finalize(
    plan_address: Annotated[str, typer.Option("--plan-address")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Move a plan out of drafting into ready."""
    store = store_for("finalize", legacy={"--plan-dir": plan_dir}, spec={}, plan=raw_plan_of(plan_address))
    if store is Store.LEDGER:
        with _ledger() as conn:
            _emit_transition(ledger.finalize(conn, _plan_of(plan_address)))
        return
    backend = _backend()
    plan_ref, task_ref = _address(plan_address, backend)
    if task_ref is not None:
        _error("--plan-address must identify a plan, not a task")
    try:
        _emit(operations.finalize_plan(backend, plan_ref))
    except (PlanNotFoundError, FileNotFoundError, FormatDetectionError, BookendValidationError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)


@app.command("validate")
def validate(
    plan_address: Annotated[str | None, typer.Option("--plan-address")] = None,
    address: Annotated[str | None, typer.Option("--address")] = None,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Print one plan's findings: the ledger's structural ones, or the content store's gaps."""
    if (plan_address is None) == (address is None):
        _error("provide --plan-address for the ledger or --address for the content store, not both and not neither")
    store = store_for(
        "validate", legacy={"--address": address, "--plan-dir": plan_dir}, spec={"--plan-address": plan_address}
    )
    if store is Store.LEDGER:
        with _ledger() as conn:
            _emit(ledger.validate(conn, _plan_of(str(plan_address))))
        return
    backend = _backend()
    plan_ref, _ = _address(str(address), backend)
    try:
        result = operations.read_plan(backend, plan_ref)
    except (PlanNotFoundError, FileNotFoundError, FormatDetectionError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)
    except (ValueError, TypeError) as exc:
        _emit({"valid": False, "errors": [str(exc)], "warnings": []})
        raise typer.Exit(1) from None
    errors: list[str] = []
    warnings: list[str] = []
    for gap in result.gaps:
        message = f"[{gap.task_id}] {gap.field_name}: {gap.gap_type} (expected: {gap.expected})"
        (errors if gap.gap_type in {"missing", "invalid_type", "invalid_value"} else warnings).append(message)
    _emit({"valid": not errors, "errors": errors, "warnings": warnings})
    if errors:
        raise typer.Exit(1)


@app.command("list")
def list_plans(
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
    search: Annotated[str | None, typer.Option("--search")] = None,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
    limit: Annotated[int | None, typer.Option("--limit", min=1)] = None,
    filters: Annotated[list[str] | None, typer.Option("--filter")] = None,
) -> None:
    """List every plan row, from the ledger or from the content store."""
    store = store_for(
        "list",
        legacy={"--plan-dir": plan_dir, "--search": search, "--offset": offset, "--limit": limit, "--filter": filters},
        spec={},
    )
    if store is Store.LEDGER:
        with _ledger() as conn:
            rows = ledger.list_plans(conn)
            _emit({"items": rows, "count": len(rows)})
        return
    filter_by_key: dict[str, str] | None = None
    if filters:
        filter_by_key = {}
        for item in filters:
            key, separator, value = item.partition("=")
            if not separator or not key:
                _error(f"--filter expects 'key=value', got: {item!r}")
            filter_by_key[key] = value
    result = operations.list_plans(_backend(), search=search, offset=offset, limit=limit, filter_by_key=filter_by_key)
    _emit({
        "items": [item.model_dump(mode="json", by_alias=True, exclude_none=True) for item in result],
        "count": len(result),
        "total": len(result),
    })


@app.command("status")
def status(
    plan_address: Annotated[str | None, typer.Option("--plan-address")] = None,
    all_plans: Annotated[bool, typer.Option("--all")] = False,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Read one plan's tasks with their derived columns and the plan's progress."""
    store = store_for(
        "status", legacy={"--all": all_plans, "--plan-dir": plan_dir}, spec={}, plan=raw_plan_of(plan_address)
    )
    if store is Store.LEDGER:
        if plan_address is None:
            _error("Provide --plan-address or --all")
        with _ledger() as conn:
            _emit(ledger.status(conn, _plan_of(plan_address)))
        return
    backend = _backend()
    if all_plans:
        results: list[dict[str, object]] = []
        for summary in operations.list_plans(backend):
            try:
                results.append(operations.get_plan_status(backend, summary.plan_id).model_dump(mode="json"))
            except _PLAN_LOAD_ERRORS as exc:
                typer.echo(f"Warning: skipping {summary.plan_id}: {exc}", err=True)
        _emit(results)
        return
    if plan_address is None:
        _error("Provide --plan-address or --all")
    plan_ref, task_ref = _address(plan_address, backend)
    if task_ref is not None:
        _error("--plan-address must identify a plan, not a task")
    try:
        _emit(operations.get_plan_status(backend, plan_ref))
    except (PlanNotFoundError, FileNotFoundError, FormatDetectionError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)


@app.command("ready")
def ready(
    plan_address: Annotated[str, typer.Option("--plan-address")],
    full: Annotated[bool, typer.Option("--full")] = False,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """List the tasks of one plan that are ready for dispatch."""
    store = store_for("ready", legacy={"--full": full, "--plan-dir": plan_dir}, spec={}, plan=raw_plan_of(plan_address))
    if store is Store.LEDGER:
        with _ledger() as conn:
            rows = ledger.ready(conn, _plan_of(plan_address))
            _emit({"items": rows, "count": len(rows)})
        return
    backend = _backend()
    plan_ref, task_ref = _address(plan_address, backend)
    if task_ref is not None:
        _error("--plan-address must identify a plan, not a task")
    try:
        _emit(operations.get_ready_tasks(backend, plan_ref, full=full))
    except (PlanNotFoundError, FileNotFoundError, FormatDetectionError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)


@app.command("archive")
def archive(
    plan_address: Annotated[str, typer.Option("--plan-address")], reason: Annotated[str, typer.Option("--reason")]
) -> None:
    """Archive a plan and close every open attempt on it."""
    with _ledger() as conn:
        _emit_transition(ledger.archive(conn, _plan_of(plan_address), reason=reason))


@app.command("from-milestone")
def from_milestone(
    milestone_number: Annotated[int, typer.Option("--milestone-number", min=1)],
    integration_branch: Annotated[str, typer.Option("--integration-branch")],
    quality_gate: Annotated[list[str] | None, typer.Option("--quality-gate")] = None,
    replace: Annotated[bool, typer.Option("--replace")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Write a milestone's open items into the ledger as one plan."""
    source = ledger.milestone_source(
        milestone_number=milestone_number,
        integration_branch=integration_branch,
        base_sha=branch_head(integration_branch),
        items=milestone_items(milestone_number),
        quality_gates=quality_gate or (),
        conflict_groups=ledger.conflict_groups_for(milestone_number),
    )
    with _ledger() as conn:
        _emit_transition(ledger.from_milestone(conn, source, replace=replace, dry_run=dry_run))


@app.command("import")
def import_plan(
    source: Annotated[str, typer.Option("--from")] = "",
    all_plans: Annotated[bool, typer.Option("--all")] = False,
    plan_address: Annotated[str | None, typer.Option("--plan-address")] = None,
    replace: Annotated[bool, typer.Option("--replace")] = False,
) -> None:
    """Write plans read from a content record or a legacy file into the ledger."""
    kind = source or flag_values("import", "--from")[0]
    plans = import_sources(kind, plan_address, all_plans=all_plans)
    with _ledger() as conn, ledger.transaction(conn):
        # One transaction across every plan: `import_plan` opens its own, and `store.transaction`
        # joins an open one rather than nesting, so a refusal on the fifth plan of `--all` rolls
        # back the four before it instead of leaving a half-imported ledger behind.
        results = [ledger.import_plan(conn, plan, replace=replace) for plan in plans]
    _emit(results)


@app.command("export")
def export_plan(
    plan_address: Annotated[str, typer.Option("--plan-address")],
    target: Annotated[str, typer.Option("--to")] = EXPORT_TARGETS[0],
) -> None:
    """Write a plan's projection to a target, or report that nothing changed."""
    if target not in EXPORT_TARGETS:
        _error(f"--to must be one of {', '.join(EXPORT_TARGETS)}, got: {target!r}")
    with _ledger() as conn:
        _emit_transition(
            ledger.export_plan(conn, _plan_of(plan_address), target=target, projection_store=ledger.content_store())
        )


# ---------------------------------------------------------------------------
# Task-scoped commands
# ---------------------------------------------------------------------------


@app.command("update")
def update(
    plan_address: Annotated[str, typer.Option("--plan-address")],
    task_id: Annotated[str | None, typer.Option("--task-id")] = None,
    attempt: Annotated[int | None, typer.Option("--attempt", min=1)] = None,
    append_section: Annotated[str | None, typer.Option("--append-section")] = None,
    section_content: Annotated[str | None, typer.Option("--section-content")] = None,
    set_values: Annotated[list[str] | None, typer.Option("--set")] = None,
    context: Annotated[str | None, typer.Option("--context")] = None,
    feature: Annotated[str | None, typer.Option("--feature")] = None,
    version: Annotated[str | None, typer.Option("--version")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    state_value: Annotated[PlanState | None, typer.Option("--state")] = None,
    goal: Annotated[str | None, typer.Option("--goal")] = None,
    acceptance_criteria_structured_json: Annotated[
        str | None, typer.Option("--acceptance-criteria-structured-json")
    ] = None,
    issue: Annotated[str | None, typer.Option("--issue")] = None,
    owner_reference: Annotated[str | None, typer.Option("--owner-reference")] = None,
    autonomy: Annotated[Literal["full_auto", "checkpoint", "per_task"] | None, typer.Option("--autonomy")] = None,
    title: Annotated[str | None, typer.Option("--title")] = None,
    task_status: Annotated[TaskStatus | None, typer.Option("--task-status")] = None,
    agent: Annotated[str | None, typer.Option("--agent")] = None,
    priority: Annotated[Priority | None, typer.Option("--priority")] = None,
    complexity: Annotated[Complexity | None, typer.Option("--complexity")] = None,
    dependency: Annotated[list[str] | None, typer.Option("--dependency")] = None,
    skill: Annotated[list[str] | None, typer.Option("--skill")] = None,
    completed: Annotated[str | None, typer.Option("--completed")] = None,
    last_activity: Annotated[str | None, typer.Option("--last-activity")] = None,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Set plan or task fields and append a task section, renewing the lease when asked."""
    store = store_for(
        "update",
        legacy={
            "--context": context,
            "--feature": feature,
            "--version": version,
            "--description": description,
            "--state": state_value,
            "--goal": goal,
            "--acceptance-criteria-structured-json": acceptance_criteria_structured_json,
            "--issue": issue,
            "--owner-reference": owner_reference,
            "--autonomy": autonomy,
            "--title": title,
            "--task-status": task_status,
            "--agent": agent,
            "--priority": priority,
            "--complexity": complexity,
            "--dependency": dependency,
            "--skill": skill,
            "--completed": completed,
            "--last-activity": last_activity,
            "--plan-dir": plan_dir,
        },
        spec={"--attempt": attempt, "--set": set_values},
        plan=raw_plan_of(plan_address),
    )
    if store is Store.CONTENT:
        content_update(
            plan_address,
            task_id,
            context,
            feature,
            version,
            description,
            state_value,
            goal,
            acceptance_criteria_structured_json,
            issue,
            owner_reference,
            autonomy,
            title,
            task_status,
            agent,
            priority,
            complexity,
            dependency,
            skill,
            append_section,
            section_content,
            completed,
            last_activity,
        )
        return
    plan_ref, _, address_task = plan_address.partition("/")
    task = task_id or (f"T{address_task.strip()}" if address_task.strip().isdigit() else address_task.strip() or None)
    columns = ledger.TASK_FIELD_COLUMNS if task is not None else ledger.PLAN_FIELD_COLUMNS
    with _ledger() as conn:
        _emit_transition(
            ledger.update(
                conn,
                plan_ref.strip(),
                task,
                attempt=attempt,
                section=append_section,
                section_content=section_content,
                values=_set_values(set_values, columns),
            )
        )


@app.command("read")
def read(
    address: Annotated[str, typer.Option("--address")],
    attempt: Annotated[int | None, typer.Option("--attempt", min=1)] = None,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Read a plan or a task, renewing the lease when an attempt is named."""
    store = store_for("read", legacy={"--plan-dir": plan_dir}, spec={"--attempt": attempt}, plan=raw_plan_of(address))
    if store is Store.LEDGER:
        plan_ref, task_ref = _task_of(address)
        with _ledger() as conn:
            _emit_transition(ledger.read(conn, plan_ref, task_ref, attempt=attempt))
        return
    backend = _backend()
    plan_ref, optional_task = _address(address, backend)
    try:
        if optional_task is None:
            _emit(operations.read_plan(backend, plan_ref))
        else:
            task_id = f"T{optional_task}" if optional_task.isdigit() else optional_task
            _emit(operations.read_task(backend, plan_ref, task_id))
    except (PlanNotFoundError, TaskNotFoundError, FileNotFoundError, FormatDetectionError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)


@app.command("dispatch")
def dispatch(
    address: Annotated[str, typer.Option("--address")],
    ttl: Annotated[int | None, typer.Option("--ttl", min=1)] = None,
    worktree: Annotated[str | None, typer.Option("--worktree")] = None,
) -> None:
    """Open an attempt on a ready task and print the new attempt number."""
    plan_ref, task_ref = _task_of(address)
    with _ledger() as conn:
        result = ledger.dispatch(conn, plan_ref, task_ref, ttl_seconds=ttl, worktree=worktree)
        typer.echo(str(result.attempt))


@app.command("renew")
def renew(
    address: Annotated[str | None, typer.Option("--address")] = None,
    attempt: Annotated[int | None, typer.Option("--attempt", min=1)] = None,
    path: Annotated[str | None, typer.Option("--path")] = None,
) -> None:
    """Push out the lease of the attempt named by an attempt number or by a worktree path."""
    plan_ref, task_ref = _optional_task_of(address)
    with _ledger() as conn:
        _emit_transition(ledger.renew(conn, plan_ref, task_ref, attempt=attempt, path=path))


@app.command("finish")
def finish(
    address: Annotated[str, typer.Option("--address")],
    attempt: Annotated[int, typer.Option("--attempt", min=1)],
    result: Annotated[str, typer.Option("--result")],
    note: Annotated[str | None, typer.Option("--note")] = None,
) -> None:
    """Close an attempt with its outcome; the runner's last command."""
    plan_ref, task_ref = _task_of(address)
    with _ledger() as conn:
        _emit_transition(ledger.finish(conn, plan_ref, task_ref, attempt=attempt, result=result, note=note))


@app.command("settle")
def settle(
    address: Annotated[str | None, typer.Option("--address")] = None,
    attempt: Annotated[int | None, typer.Option("--attempt", min=1)] = None,
    path: Annotated[str | None, typer.Option("--path")] = None,
    return_text: Annotated[str | None, typer.Option("--return-text")] = None,
) -> None:
    """Record what the harness call returned for one attempt."""
    plan_ref, task_ref = _optional_task_of(address)
    with _ledger() as conn:
        _emit_transition(ledger.settle(conn, plan_ref, task_ref, attempt=attempt, path=path, return_text=return_text))


@app.command("accept")
def accept(
    address: Annotated[str, typer.Option("--address")],
    note: Annotated[str | None, typer.Option("--note")] = None,
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Accept a complete task, completing a returned one first."""
    plan_ref, task_ref = _task_of(address)
    with _ledger() as conn:
        _emit_transition(ledger.accept(conn, plan_ref, task_ref, note=note, force=force))


@app.command("reclaim")
def reclaim(
    address: Annotated[str, typer.Option("--address")],
    reason: Annotated[str, typer.Option("--reason")],
    response: Annotated[str | None, typer.Option("--response")] = None,
    force: Annotated[bool, typer.Option("--force")] = False,
    more_attempts: Annotated[bool, typer.Option("--more-attempts")] = False,
) -> None:
    """Send a task back to not-started for another attempt."""
    plan_ref, task_ref = _task_of(address)
    with _ledger() as conn:
        _emit_transition(
            ledger.reclaim(
                conn, plan_ref, task_ref, reason=reason, response=response, force=force, more_attempts=more_attempts
            )
        )


@app.command("state")
def state(
    address: Annotated[str, typer.Option("--address")],
    new_status: Annotated[TaskStatus, typer.Option("--new-status")],
    reason: Annotated[str | None, typer.Option("--reason")] = None,
    force: Annotated[bool, typer.Option("--force")] = False,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Move a task to a new status without a runner."""
    store = store_for(
        "state", legacy={"--plan-dir": plan_dir}, spec={"--reason": reason, "--force": force}, plan=raw_plan_of(address)
    )
    if store is Store.LEDGER:
        if reason is None:
            _error("--reason is required: the ledger records why a status moved without a runner")
        plan_ref, task_ref = _task_of(address)
        with _ledger() as conn:
            _emit_transition(
                ledger.state(conn, plan_ref, task_ref, new_status=str(new_status), reason=reason, force=force)
            )
        return
    backend = _backend()
    plan_ref, optional_task = _address(address, backend)
    if optional_task is None:
        _error(f"Address '{address}' does not include a task component")
    task_id = f"T{optional_task}" if optional_task.isdigit() else optional_task
    try:
        result = operations.update_task_status(backend, plan_ref, task_id, new_status)
    except (PlanNotFoundError, TaskNotFoundError, FileNotFoundError, FormatDetectionError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)
    _emit(result)


# ---------------------------------------------------------------------------
# ledger_spec.RETIRED_COMMANDS: unchanged until the slice that deletes them
# ---------------------------------------------------------------------------


@app.command("claim")
def claim(
    address: Annotated[str, typer.Option("--address")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Claim a task by transitioning it to in-progress."""
    backend = _backend()
    plan_ref, task_ref = _address(address, backend)
    if task_ref is None:
        _error(f"Address '{address}' does not include a task component")
    task_id = f"T{task_ref}" if task_ref.isdigit() else task_ref
    try:
        _emit(operations.claim_task(backend, plan_ref, task_id))
    except (PlanNotFoundError, TaskNotFoundError, FileNotFoundError, FormatDetectionError, ValueError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)


def _canonical_output_path(plan_path: Path) -> Path:
    """Return the canonical YAML destination for a legacy plan path."""
    if plan_path.is_dir():
        return plan_path
    match = re.match(r"^tasks-(\d+)-(.+)\.md$", plan_path.name)
    if match:
        return plan_path.parent / f"P{int(match.group(1)):03d}-{match.group(2)}.yaml"
    return plan_path.with_suffix(".yaml")


def _extract_fallback_metadata(raw_content: str, plan_path: Path) -> tuple[int, str, str, int | None]:
    """Extract minimal metadata when a legacy plan cannot be parsed.

    Returns:
        Plan number, slug, goal, and optional issue number.
    """
    match = re.match(r"^tasks-(\d+)-(.+)\.md$", plan_path.name)
    number = int(match.group(1)) if match else 0
    slug = match.group(2) if match else plan_path.stem
    goal = slug.replace("-", " ").title()
    heading = re.search(r"^#\s+(.+)$", raw_content, re.MULTILINE)
    if heading:
        goal = heading.group(1).strip()
    issue_match = re.search(r"(?:\*\*Issue\*\*|^issue):\s*#?(\d+)", raw_content, re.MULTILINE)
    return number, slug, goal, int(issue_match.group(1)) if issue_match else None


def _migrate_one_fallback(plan_path: Path, dry_run: bool) -> tuple[Path | None, str]:
    """Preserve an unparseable legacy plan as canonical YAML.

    Returns:
        Written path (or ``None`` for dry runs) and source format.
    """
    output_path = _canonical_output_path(plan_path)
    if output_path != plan_path and output_path.exists():
        message = f"Skipping {plan_path.name}: target {output_path.name} already exists"
        typer.echo(message, err=True)
        if not dry_run:
            raise FileExistsError(message)
        return None, "fallback-preservation"
    raw_content = plan_path.read_text(encoding="utf-8", errors="replace")
    number, slug, goal, issue = _extract_fallback_metadata(raw_content, plan_path)
    if dry_run:
        typer.echo(f"Would migrate (fallback): {plan_path}", err=True)
        return None, "fallback-preservation"
    data: dict[str, object] = {
        "plan_number": number,
        "slug": slug,
        "goal": goal,
        "status": "complete",
        "tasks": [],
        "context": {"source_file": plan_path.name, "body": raw_content},
    }
    if issue is not None:
        data["issue"] = issue
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 2**31 - 1
    stream = io.StringIO()
    yaml.dump(data, stream)
    output_path.write_text(stream.getvalue(), encoding="utf-8")
    typer.echo(f"Migrated (fallback) {plan_path} -> {output_path}", err=True)
    return output_path, "fallback-preservation"


def _migrate_one(plan_path: Path, dry_run: bool) -> tuple[Path | None, str]:
    """Migrate one plan, falling back to content-preserving conversion.

    Returns:
        Written path (or ``None`` for dry runs) and source format.
    """
    plan_ref = plan_id_from_path(plan_path)
    try:
        result = operations.read_plan(_backend(), plan_ref)
    except _PLAN_LOAD_ERRORS:
        return _migrate_one_fallback(plan_path, dry_run)
    output_path = _canonical_output_path(plan_path)
    if output_path != plan_path and output_path.exists():
        message = f"Skipping {plan_path.name}: target {output_path.name} already exists"
        typer.echo(message, err=True)
        if not dry_run:
            raise FileExistsError(message)
        return None, result.source_format
    if dry_run:
        typer.echo(f"Would migrate: {plan_path}", err=True)
        return None, result.source_format
    written = write_plan(result.plan, output_path)
    typer.echo(f"Migrated {plan_path} -> {written}", err=True)
    return written, result.source_format


def _update_backlog_refs(old_path: Path, new_path: Path, backlog_dir: Path) -> int:
    """Update matching plan references in backlog frontmatter.

    Returns:
        Number of references updated.
    """
    if not backlog_dir.exists():
        return 0
    updated = 0
    yaml = YAML()
    yaml.preserve_quotes = True
    for md_file in sorted(backlog_dir.glob("*.md")):
        try:
            raw = md_file.read_text(encoding="utf-8")
            parts = raw.split("---", 2)
            if not raw.startswith("---") or len(parts) < _YAML_FRONTMATTER_PARTS:
                continue
            frontmatter = yaml.load(parts[1])
            if not isinstance(frontmatter, dict) or str(frontmatter.get("plan", "")) != str(old_path):
                continue
            frontmatter["plan"] = str(new_path)
            stream = io.StringIO()
            yaml.dump(frontmatter, stream)
            md_file.write_text(f"---\n{stream.getvalue()}---{parts[2]}", encoding="utf-8")
            updated += 1
        except (OSError, YAMLError):
            continue
    return updated


def _attempt_backlog_sync() -> None:
    """Best-effort backlog sync before bulk migration."""
    if _BACKLOG_CORE_AVAILABLE:
        try:
            _sync_backlog()
        except _SYNC_ERRORS as exc:
            typer.echo(f"Warning: backlog sync failed; continuing. ({exc})", err=True)
        else:
            typer.echo("Backlog synced to GitHub.", err=True)
            return
    uv_exe = shutil.which("uv")
    if not uv_exe:
        typer.echo("Warning: backlog sync unavailable (uv not found).", err=True)
        return
    try:
        process = subprocess.run(
            [uv_exe, "run", "backlog", "sync"], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        typer.echo(f"Warning: backlog sync unavailable: {exc}", err=True)
    else:
        if process.returncode:
            typer.echo(f"Warning: backlog sync failed (exit {process.returncode}): {process.stderr.strip()}", err=True)
        else:
            typer.echo("Backlog synced to GitHub.", err=True)


def _migrate_all(
    plan_dir: Path, dry_run: bool, skip_sync: bool, backlog_dir: Path
) -> dict[str, str | int | bool | list[str]]:
    """Migrate every legacy plan in a directory and return a JSON summary.

    Returns:
        Compact-JSON-compatible migration summary.
    """
    if not plan_dir.exists():
        _error(f"Plan directory does not exist: {plan_dir}")
    candidates = sorted(p for p in plan_dir.iterdir() if p.suffix == ".md" and re.match(r"^tasks-\d+-", p.name))
    if not candidates:
        return {"migrated": 0, "candidates": 0, "backlog_refs_updated": 0, "dry_run": dry_run}
    if not skip_sync and not dry_run:
        _attempt_backlog_sync()
    migrated: list[tuple[Path, Path]] = []
    errors: list[str] = []
    for path in candidates:
        try:
            written, _ = _migrate_one(path, dry_run)
        except (*_PLAN_LOAD_ERRORS, OSError) as exc:
            errors.append(f"{path.name}: {exc}")
            typer.echo(f"Error migrating {path.name}: {exc}", err=True)
        else:
            if written is not None:
                migrated.append((path, written))
    references = 0 if dry_run else sum(_update_backlog_refs(old, new, backlog_dir) for old, new in migrated)
    return {
        "migrated": len(migrated),
        "candidates": len(candidates),
        "backlog_refs_updated": references,
        "errors": errors,
        "dry_run": dry_run,
    }


@app.command("migrate")
def migrate(
    plan_address: Annotated[str | None, typer.Option("--plan-address")] = None,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    all_plans: Annotated[bool, typer.Option("--all")] = False,
    skip_sync: Annotated[bool, typer.Option("--skip-sync")] = False,
    backlog_dir: Annotated[Path | None, typer.Option("--backlog-dir")] = None,
) -> None:
    """Migrate one legacy plan or all legacy plans to canonical YAML."""
    directory = _plan_dir(plan_dir)
    if all_plans:
        _emit(
            _migrate_all(directory, dry_run, skip_sync, dh_paths.backlog_dir() if backlog_dir is None else backlog_dir)
        )
        return
    if plan_address is None:
        _error("Provide --plan-address or use --all to migrate every plan")
    plan_ref, task_ref = _address(plan_address)
    if task_ref is not None:
        _error("--plan-address must identify a plan, not a task")
    try:
        path = resolve_plan_address(plan_ref, directory)
        written, source_format = _migrate_one(path, dry_run)
    except (AddressingError, FileNotFoundError, FormatDetectionError, ValueError, OSError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)
    _emit({
        "migrated": written is not None,
        "path": str(written or path),
        "source_format": source_format,
        "dry_run": dry_run,
    })


def _repeatable(values: list[str] | None, option_name: str, *, required: bool = False) -> list[str]:
    """Validate repeatable string options at the CLI boundary.

    Returns:
        The validated values, or an empty list when the option was omitted.
    """
    if values is None:
        if required:
            cli_output.err(f"{option_name} must be provided at least once")
        return []
    if any(not value.strip() for value in values):
        cli_output.err(f"{option_name} values must not be empty")
    return values


def _emit_sam_result(result: object, output: Output) -> None:
    """Emit operation data on stdout and collected diagnostics on stderr."""
    cli_output.output_json(result)
    for message in output.messages:
        typer.echo(message, err=True)
    for warning in output.warnings:
        typer.echo(warning, err=True)
    for error in output.errors:
        typer.echo(error, err=True)


@app.command("sam-task-create")
def sam_task_create(
    parent_issue_number: Annotated[int, typer.Option("--parent-issue-number", min=1)],
    task_id: Annotated[str, typer.Option("--task-id")],
    feature: Annotated[str, typer.Option("--feature")],
    task_type: Annotated[str, typer.Option("--task-type")],
    agent: Annotated[str, typer.Option("--agent")],
    priority: Annotated[int, typer.Option("--priority", min=1, max=5)],
    description: Annotated[str, typer.Option("--description")],
    skills: Annotated[list[str] | None, typer.Option("--skill")] = None,
    dependencies: Annotated[list[str] | None, typer.Option("--dependency")] = None,
    acceptance_criteria: Annotated[list[str] | None, typer.Option("--acceptance-criterion")] = None,
    labels: Annotated[list[str] | None, typer.Option("--label")] = None,
    repo: Annotated[str, typer.Option("--repo")] = "",
) -> None:
    """Create one SAM task under a parent issue."""
    output = Output()
    result = operations.create_sam_task(
        parent_issue_number=parent_issue_number,
        repo=repo,
        task_id=task_id,
        feature=feature,
        task_type=task_type,
        agent=agent,
        priority=priority,
        skills=_repeatable(skills, "--skill"),
        dependencies=_repeatable(dependencies, "--dependency"),
        description=description,
        acceptance_criteria=_repeatable(acceptance_criteria, "--acceptance-criterion"),
        labels=_repeatable(labels, "--label"),
        output=output,
    )
    _emit_sam_result(result, output)


@app.command("sam-tasks")
def sam_tasks(
    parent_issue_number: Annotated[int, typer.Option("--parent-issue-number", min=1)],
    refresh_cache: Annotated[bool, typer.Option("--refresh-cache/--no-refresh-cache")] = True,
    repo: Annotated[str, typer.Option("--repo")] = "",
) -> None:
    """List SAM tasks under a parent issue."""
    output = Output()
    result = operations.get_sam_tasks(
        parent_issue_number=parent_issue_number, refresh_cache=refresh_cache, repo=repo, output=output
    )
    _emit_sam_result(result, output)


@app.command("sam-task-status")
def sam_task_status(
    issue_number: Annotated[int, typer.Option("--issue-number", min=1)],
    new_status: Annotated[str, typer.Option("--new-status")],
    repo: Annotated[str, typer.Option("--repo")] = "",
) -> None:
    """Update a SAM task status."""
    if not new_status.strip():
        cli_output.err("--new-status must not be empty")
    output = Output()
    result = operations.update_sam_task_status(
        issue_number=issue_number, new_status=new_status, repo=repo, output=output
    )
    _emit_sam_result(result, output)


@app.command("sam-ready-tasks")
def sam_ready_tasks(
    parent_issue_number: Annotated[int, typer.Option("--parent-issue-number", min=1)],
    repo: Annotated[str, typer.Option("--repo")] = "",
) -> None:
    """List SAM tasks ready to start."""
    output = Output()
    result = operations.get_ready_sam_tasks(parent_issue_number=parent_issue_number, repo=repo, output=output)
    _emit_sam_result(result, output)


check_import_sources()
check_groomed_fields()
check_surface()

__all__ = ["app"]

if __name__ == "__main__":
    app()

# ponytail: two stores, one group; the flags a caller passes say which one answers.
