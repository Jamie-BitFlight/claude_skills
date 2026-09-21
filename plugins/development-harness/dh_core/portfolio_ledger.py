"""Canonical portfolio merge ledger models and transition service."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
import urllib.request
from collections.abc import Iterator
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from threading import Lock
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

if os.name == "nt":
    import msvcrt
else:
    import fcntl

THREAD_LOCKS: dict[Path, Lock] = {}
THREAD_LOCKS_GUARD = Lock()

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
GitSha = Annotated[str, Field(pattern=r"^[0-9a-f]{40,64}$")]

CANONICAL_CONFLICT_GROUP_IDS = frozenset({
    "CG-PORTFOLIO-LEDGER",
    "CG-CORE-CONTRACT",
    "CG-CORE-OPS",
    "CG-LEDGER-FACADE",
    "CG-PLAN-FRONTEND",
    "CG-PARITY-MATRIX",
    "CG-ARCH-GATE",
    "CG-CLI-DISPATCH",
    "CG-DISPATCH-STATE",
    "CG-BACKLOG-LISTING",
    "CG-BACKLOG-SERVER",
    "CG-A4-TRANSPORT",
    "CG-GITHUB-PROVIDER",
    "CG-GITHUB-CONTENTS",
    "CG-PROGRESSIVE-MARKDOWN-NAVIGATION",
    "CG-DH-ARCH",
    "CG-WORKFLOW-SOURCES",
    "CG-WORKFLOW-GENERATED",
    "CG-PYTEST-POLICY",
    "CG-COMPATIBILITY",
    "CG-CLI-BOOTSTRAP",
    "CG-RESEARCH-PROVENANCE",
    "CG-HEALTH-DIAGNOSTICS",
    "CG-REDACTION-PRIMITIVE",
    "CG-PLUGIN-CREATOR-TESTS",
    "CG-OPENCODE-ARCH",
    "CG-OPENCODE-INSTALL",
    "CG-OPENCODE-SMOKE",
    "CG-A11-HANDOFF-SOURCES",
    "CG-A11-PORTABILITY-TESTS",
    "CG-TRACKER-STATE",
})


class LedgerModel(BaseModel):
    """Strict base model for every persisted ledger record."""

    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class CarState(StrEnum):
    """Legal states for a merge-train car."""

    INVENTORIED = "INVENTORIED"
    RESERVED = "RESERVED"
    IMPLEMENTATION_ADMITTED = "IMPLEMENTATION_ADMITTED"
    INTEGRATED = "INTEGRATED"
    ASPECT_CERTIFIED = "ASPECT_CERTIFIED"


class ParentState(StrEnum):
    """Legal states for the portfolio parent."""

    INVENTORIED = "INVENTORIED"
    PARENT_CERTIFIED = "PARENT_CERTIFIED"


class CarKind(StrEnum):
    """Kinds of merge-train cars."""

    FOUNDATION = "foundation"
    PRODUCER = "producer"
    IMPLEMENTATION = "implementation"
    ASPECT_AGGREGATE = "aspect_aggregate"


class ReservationState(StrEnum):
    """Lifecycle of a resource reservation."""

    ACTIVE = "active"
    RELEASED = "released"
    INVALIDATED = "invalidated"


class Verdict(StrEnum):
    """Verdicts carried by immutable evidence receipts."""

    PASSED = "PASS"
    REFUSED = "REFUSED"
    BLOCKED = "BLOCKED"
    RECORDED = "RECORDED"


class TrackerManifest(LedgerModel):
    """Identity of the tracker authority consumed by the ledger."""

    path: str
    sha256: Sha256
    observed_at: datetime


class CorrectionRow(LedgerModel):
    """One corrected planning input and its independent review."""

    owner: str
    artifact: str
    sha256: Sha256
    reviewer: str
    verdict: Verdict = Verdict.PASSED


class Role(LedgerModel):
    """One actor identity bound to an independence class."""

    id: str
    session: str
    independence_class: Literal["maker", "checker", "integrator", "parent-checker", "ledger-writer"]


class InventoryPath(LedgerModel):
    """One exact path in a frozen inventory."""

    path: str
    git_blob: GitSha
    sha256: Sha256


class Inventory(LedgerModel):
    """A sorted, content-addressed resource inventory."""

    id: str
    revision: GitSha
    paths: list[InventoryPath]
    sha256: Sha256


def inventory_sha256(paths: list[InventoryPath]) -> str:
    """Compute the canonical digest for an exact inventory path list.

    Args:
        paths: Ordered inventory paths.

    Returns:
        Lowercase SHA-256 hex digest.
    """
    payload = json.dumps(
        [item.model_dump(mode="json") for item in paths], ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ConflictGroup(LedgerModel):
    """Canonical reservation group and its primary resources."""

    id: str
    paths: list[str]


class Reservation(LedgerModel):
    """Exclusive claim over exact primary resources."""

    id: str
    group: str
    paths: list[str]
    owner: str
    state: ReservationState
    lock_path: str
    acquired_at: datetime
    released_at: datetime | None = None
    invalidated_at: datetime | None = None
    receipt_sha256: Sha256


class RecoveryEvidence(LedgerModel):
    """Evidence required to invalidate a stale owner's reservation."""

    stale_owner_id: str
    process_id: int = Field(gt=0)
    liveness_output_path: str
    liveness_output_sha256: Sha256
    prior_receipt_sha256: Sha256
    checker_id: str
    judgement_path: str
    judgement_sha256: Sha256
    observed_at: datetime


class CommandEvidence(LedgerModel):
    """Complete command result referenced by immutable output bytes."""

    argv: list[str] = Field(min_length=1)
    exit_code: int
    output_path: str
    output_sha256: Sha256


class EvidenceReceipt(LedgerModel):
    """Immutable maker, checker, integrator, or recovery evidence."""

    path: str
    sha256: Sha256
    author_id: str
    verdict: Verdict
    observed_revision: GitSha | None = None


class HistoryEvent(LedgerModel):
    """One accepted ledger mutation."""

    action: str
    actor_id: str
    at: datetime
    from_state: str
    to_state: str
    receipt_sha256: Sha256


class Car(LedgerModel):
    """One implementation, producer, foundation, or aggregate train car."""

    id: str
    issue: int = Field(gt=0)
    aspect: str
    car_kind: CarKind
    required_for_parent: bool
    aspect_membership: list[str] = Field(min_length=1)
    state: CarState
    base_git_sha: GitSha
    upstream_git_sha: GitSha
    predecessor_shas: list[GitSha] = Field(default_factory=list)
    implementation_sha: GitSha | None = None
    maker_id: str
    implementation_checker_id: str | None = None
    implementation_report: str | None = None
    integration_sha: GitSha | None = None
    integrator_id: str | None = None
    aspect_checker_id: str | None = None
    aspect_report: str | None = None
    commands: list[CommandEvidence] = Field(default_factory=list)
    inventory_ids: list[str] = Field(default_factory=list)
    reservation_ids: list[str] = Field(default_factory=list)
    receipts: list[EvidenceReceipt] = Field(default_factory=list)
    history: list[HistoryEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_state_evidence(self) -> Car:
        """Require every persisted state to carry all earlier transition evidence.

        Returns:
            Validated car.
        """
        if self.state is CarState.RESERVED and not self.reservation_ids:
            raise ValueError("RESERVED car requires an active reservation reference")
        admitted_or_later = self.state in {
            CarState.IMPLEMENTATION_ADMITTED,
            CarState.INTEGRATED,
            CarState.ASPECT_CERTIFIED,
        }
        if admitted_or_later and not all((
            self.implementation_sha,
            self.implementation_checker_id,
            self.implementation_report,
            self.commands,
        )):
            raise ValueError(f"{self.state} car lacks IMPLEMENTATION_ADMITTED evidence")
        integrated_or_later = self.state in {CarState.INTEGRATED, CarState.ASPECT_CERTIFIED}
        if integrated_or_later and not all((self.integration_sha, self.integrator_id)):
            raise ValueError(f"{self.state} car lacks INTEGRATED evidence")
        if self.state is CarState.ASPECT_CERTIFIED:
            if self.car_kind is not CarKind.ASPECT_AGGREGATE:
                raise ValueError("ASPECT_CERTIFIED is legal only for an aspect aggregate")
            if not all((self.aspect_checker_id, self.aspect_report)):
                raise ValueError("ASPECT_CERTIFIED car lacks aspect checker evidence")
        return self


class Addendum(LedgerModel):
    """Exact-revision evidence required after aspect certification."""

    id: str
    car_id: str
    revision: GitSha
    checker_id: str
    report: str
    receipt: EvidenceReceipt


class Parent(LedgerModel):
    """Parent-only certification state."""

    state: ParentState
    checker_id: str | None = None
    revision: GitSha | None = None
    report: str | None = None
    required_car_ids: list[str]
    required_addendum_ids: list[str] = Field(default_factory=list)
    addenda: list[Addendum] = Field(default_factory=list)
    receipt: EvidenceReceipt | None = None

    @model_validator(mode="after")
    def validate_certification_evidence(self) -> Parent:
        """Reject a persisted certification claim without its complete verdict.

        Returns:
            Validated parent record.
        """
        if self.state is ParentState.PARENT_CERTIFIED and not all((
            self.checker_id,
            self.revision,
            self.report,
            self.receipt,
        )):
            raise ValueError("PARENT_CERTIFIED requires complete parent certification evidence")
        return self


class Mirror(LedgerModel):
    """Immutable mirror binding for the latest accepted ledger bytes."""

    url: str | None = None
    expected_sha256: Sha256 | None = None


class PortfolioLedger(LedgerModel):
    """Complete reconstructable state of the runtime-integrity merge train."""

    schema_version: Literal[1] = 1
    portfolio_issue: int = Field(gt=0)
    tracker_manifest: TrackerManifest
    correction_rows: dict[str, CorrectionRow]
    roles: dict[str, Role]
    conflict_groups: dict[str, ConflictGroup] = Field(default_factory=dict)
    inventories: dict[str, Inventory] = Field(default_factory=dict)
    reservations: dict[str, Reservation] = Field(default_factory=dict)
    cars: dict[str, Car]
    parent: Parent
    mirror: Mirror
    ledger_sha256: Sha256 | None = None

    @model_validator(mode="after")
    def validate_corrections_and_roles(self) -> PortfolioLedger:
        """Reject incomplete corrections and mismatched role keys.

        Returns:
            Validated ledger.
        """
        expected_rows = {f"R{number:02d}" for number in range(1, 22)}
        if set(self.correction_rows) != expected_rows:
            raise ValueError("correction_rows must contain exactly R01 through R21")
        for key, role in self.roles.items():
            if key != role.id:
                raise ValueError(f"role key {key!r} does not match role id {role.id!r}")
        return self

    @model_validator(mode="after")
    def validate_conflict_groups(self) -> PortfolioLedger:
        """Reject aliases and duplicate primary path ownership.

        Returns:
            Validated ledger.
        """
        primary_paths: dict[str, str] = {}
        unknown_groups = set(self.conflict_groups) - CANONICAL_CONFLICT_GROUP_IDS
        if unknown_groups:
            raise ValueError(f"unknown conflict groups or aliases: {sorted(unknown_groups)}")
        for key, group in self.conflict_groups.items():
            if key != group.id:
                raise ValueError(f"conflict-group key {key!r} does not match group id {group.id!r}")
            if len(group.paths) != len(set(group.paths)):
                raise ValueError(f"conflict group {group.id!r} contains duplicate paths")
            for path in group.paths:
                if path in primary_paths:
                    raise ValueError(f"primary path {path!r} belongs to both {primary_paths[path]!r} and {group.id!r}")
                primary_paths[path] = group.id
        return self

    @model_validator(mode="after")
    def validate_inventories(self) -> PortfolioLedger:
        """Reject mismatched inventory keys and content digests.

        Returns:
            Validated ledger.
        """
        for key, inventory in self.inventories.items():
            if key != inventory.id:
                raise ValueError(f"inventory key {key!r} does not match inventory id {inventory.id!r}")
            if inventory.sha256 != inventory_sha256(inventory.paths):
                raise ValueError(f"inventory {inventory.id!r} digest mismatch")
        return self

    @model_validator(mode="after")
    def validate_car_and_parent_references(self) -> PortfolioLedger:
        """Reject unresolved car, inventory, maker, and parent references.

        Returns:
            Validated ledger.
        """
        for key, car in self.cars.items():
            if key != car.id:
                raise ValueError(f"car key {key!r} does not match car id {car.id!r}")
            if car.maker_id not in self.roles:
                raise ValueError(f"car {car.id!r} references unknown maker {car.maker_id!r}")
            missing_inventories = set(car.inventory_ids) - set(self.inventories)
            if missing_inventories:
                raise ValueError(f"car {car.id!r} references undefined inventories: {sorted(missing_inventories)}")
        undefined = set(self.parent.required_car_ids) - set(self.cars)
        if undefined:
            raise ValueError(f"parent references undefined required cars: {sorted(undefined)}")
        return self

    @model_validator(mode="after")
    def validate_certified_parent(self) -> PortfolioLedger:
        """Reject persisted parent verdicts that bypass portfolio prerequisites.

        Returns:
            Validated ledger.
        """
        if self.parent.state is not ParentState.PARENT_CERTIFIED:
            return self
        required_ids = {car.id for car in self.cars.values() if car.required_for_parent}
        if not required_ids or set(self.parent.required_car_ids) != required_ids:
            raise ValueError("certified parent requires the exact non-empty required car set")
        required_cars = [self.cars[car_id] for car_id in self.parent.required_car_ids]
        if any(
            car.car_kind is not CarKind.ASPECT_AGGREGATE or car.state is not CarState.ASPECT_CERTIFIED
            for car in required_cars
        ):
            raise ValueError("certified parent requires every required car to be an ASPECT_CERTIFIED aggregate")
        addendum_ids = {addendum.id for addendum in self.parent.addenda}
        if set(self.parent.required_addendum_ids) - addendum_ids:
            raise ValueError("certified parent requires every declared addendum")
        required_addenda = [
            addendum for addendum in self.parent.addenda if addendum.id in self.parent.required_addendum_ids
        ]
        for addendum in required_addenda:
            error = self.certified_addendum_error(addendum)
            if error:
                raise ValueError(f"certified parent addendum {addendum.id!r} is invalid: {error}")
        role = self.roles.get(self.parent.checker_id or "")
        receipt = self.parent.receipt
        if role is None or role.independence_class != "parent-checker":
            raise ValueError("certified parent requires parent-checker authority")
        if (
            receipt is None
            or receipt.author_id != self.parent.checker_id
            or receipt.verdict is not Verdict.PASSED
            or receipt.observed_revision != self.parent.revision
            or receipt.path != self.parent.report
        ):
            raise ValueError("certified parent requires a matching immutable verdict receipt")
        return self

    def certified_addendum_error(self, addendum: Addendum) -> str | None:
        """Return the persisted-contract error for one required addendum.

        Args:
            addendum: Required parent addendum.

        Returns:
            Error text, or ``None`` when valid.
        """
        car = self.cars.get(addendum.car_id)
        if car is None or car.state is not CarState.ASPECT_CERTIFIED:
            return "car is not an ASPECT_CERTIFIED aggregate"
        if addendum.revision != car.integration_sha:
            return "revision does not match the integrated car SHA"
        role = self.roles.get(addendum.checker_id)
        excluded = {car.maker_id, car.implementation_checker_id, car.integrator_id, car.aspect_checker_id}
        if role is None or role.independence_class != "checker" or addendum.checker_id in excluded:
            return "checker lacks independent checker authority"
        receipt = addendum.receipt
        if (
            addendum.report != receipt.path
            or receipt.author_id != addendum.checker_id
            or receipt.verdict is not Verdict.PASSED
            or receipt.observed_revision != addendum.revision
        ):
            return "immutable receipt identity, verdict, revision, or report does not match"
        return None

    def canonical_json(self, *, include_digest: bool = True) -> str:
        """Return compact, sorted, UTF-8-safe canonical JSON.

        Args:
            include_digest: Include ``ledger_sha256`` when present.

        Returns:
            Canonical JSON text.
        """
        payload = self.model_dump(mode="json", exclude_none=False)
        if not include_digest:
            payload["ledger_sha256"] = None
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    def canonical_bytes(self, *, include_digest: bool = True) -> bytes:
        """Return canonical UTF-8 bytes.

        Args:
            include_digest: Include ``ledger_sha256`` when present.

        Returns:
            Canonical bytes.
        """
        return self.canonical_json(include_digest=include_digest).encode("utf-8")

    def identity_sha256(self) -> str:
        """Return the digest of canonical content excluding self-referential digest fields.

        Returns:
            Lowercase SHA-256 hex digest.
        """
        identity = self.model_copy(
            update={"ledger_sha256": None, "mirror": self.mirror.model_copy(update={"expected_sha256": None})}
        )
        return hashlib.sha256(identity.canonical_bytes()).hexdigest()


CANONICAL_LEDGER_PATH = Path(".tmp/reports/runtime-integrity-merge-train-ledger.json")
CANONICAL_LOCK_PATH = Path(".tmp/reports/runtime-integrity-merge-train-ledger.lock")


class LedgerRefusal(ValueError):
    """A requested mutation violated the fail-closed portfolio contract."""


class LedgerStore:
    """Lock-backed atomic persistence for canonical portfolio revisions."""

    def __init__(self, ledger_path: Path, lock_path: Path) -> None:
        """Configure exact local data and persistent lock paths.

        Args:
            ledger_path: Canonical JSON execution copy.
            lock_path: Advisory lock file, retained permanently.
        """
        self.ledger_path = ledger_path
        self.lock_path = lock_path

    def read(self) -> PortfolioLedger:
        """Read and verify the canonical local revision.

        Returns:
            Reconstructed ledger.

        Raises:
            LedgerRefusal: When canonical parsing or digest verification fails.
        """
        try:
            ledger = PortfolioLedger.model_validate_json(self.ledger_path.read_bytes())
        except (OSError, ValueError) as error:
            raise LedgerRefusal(f"cannot reconstruct local ledger: {error}") from error
        if ledger.ledger_sha256 is None or ledger.identity_sha256() != ledger.ledger_sha256:
            raise LedgerRefusal("local ledger digest mismatch")
        if ledger.mirror.expected_sha256 is not None and ledger.mirror.expected_sha256 != ledger.ledger_sha256:
            raise LedgerRefusal("recorded mirror digest does not match local ledger identity")
        return ledger

    def write(self, ledger: PortfolioLedger) -> PortfolioLedger:
        """Stamp and atomically replace one canonical ledger revision.

        Args:
            ledger: Validated transition result.

        Returns:
            Persisted revision with its content identity digest.

        Raises:
            OSError: When durable write or atomic replacement fails.
        """
        with self.lock():
            return self.write_locked(ledger)

    def write_transition(self, ledger: PortfolioLedger, *, expected_ledger_sha256: str | None) -> PortfolioLedger:
        """Atomically compare and replace a transition result.

        Args:
            ledger: Transition result derived from the expected revision.
            expected_ledger_sha256: Digest observed before computing the transition.

        Returns:
            Persisted revision.

        Raises:
            LedgerRefusal: When another process has already advanced the ledger.
        """
        with self.lock():
            current = self.read()
            if current.ledger_sha256 != expected_ledger_sha256:
                raise LedgerRefusal("stale ledger revision; reload before retrying the transition")
            return self.write_locked(ledger)

    @contextlib.contextmanager
    def lock(self) -> Iterator[None]:
        """Hold the per-path thread and cross-process ledger lock."""
        self.ledger_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        resolved_lock = self.lock_path.resolve()
        with THREAD_LOCKS_GUARD:
            thread_lock = THREAD_LOCKS.setdefault(resolved_lock, Lock())
        with thread_lock:
            lock_fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
            try:
                if os.fstat(lock_fd).st_size == 0:
                    os.write(lock_fd, b"\0")
                    os.fsync(lock_fd)
                os.lseek(lock_fd, 0, os.SEEK_SET)
                if os.name == "nt":
                    msvcrt.locking(lock_fd, msvcrt.LK_LOCK, 1)
                else:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    os.lseek(lock_fd, 0, os.SEEK_SET)
                    if os.name == "nt":
                        msvcrt.locking(lock_fd, msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(lock_fd)

    def write_locked(self, ledger: PortfolioLedger) -> PortfolioLedger:
        """Durably replace the ledger while the caller holds the advisory lock.

        Returns:
            Persisted ledger with its identity digest.
        """
        ledger = PortfolioLedger.model_validate(ledger.model_dump(mode="python"))
        digest = ledger.identity_sha256()
        mirror = ledger.mirror
        if mirror.url is not None:
            mirror = mirror.model_copy(update={"expected_sha256": digest})
        stamped = ledger.model_copy(update={"ledger_sha256": digest, "mirror": mirror})
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=self.ledger_path.parent, prefix=f".{self.ledger_path.name}.", suffix=".tmp", delete=False
            ) as stream:
                temporary_path = stream.name
                stream.write(stamped.canonical_bytes())
                stream.flush()
                os.fsync(stream.fileno())
            Path(temporary_path).replace(self.ledger_path)
            temporary_path = None
            directory_fd = os.open(self.ledger_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary_path is not None:
                with contextlib.suppress(OSError):
                    Path(temporary_path).unlink()
        return stamped

    def verify_mirror(self) -> PortfolioLedger:
        """Require local and immutable mirror bytes to agree exactly.

        Returns:
            Verified local ledger.

        Raises:
            LedgerRefusal: When URL, bytes, parsing, or recorded digest disagree.
        """
        local = self.read()
        mirror_bytes = self.read_mirror_bytes(local.mirror)
        mirror = self.validate_mirror_bytes(mirror_bytes)
        if mirror_bytes != self.ledger_path.read_bytes():
            raise LedgerRefusal("local and mirror ledger bytes do not match")
        if mirror.ledger_sha256 != local.ledger_sha256:
            raise LedgerRefusal("local and mirror ledger identities do not match")
        return local

    def restore_from_mirror(self, *, mirror_url: str, expected_sha256: str | None) -> PortfolioLedger:
        """Restore a missing local copy from a self-verifying immutable mirror.

        Args:
            mirror_url: Immutable mirror location from the external portfolio record.
            expected_sha256: Identity digest recorded independently of either copy.

        Returns:
            Restored and reconstructed ledger.

        Raises:
            LedgerRefusal: When local exists or mirror verification fails.
        """
        with self.lock():
            if self.ledger_path.exists():
                raise LedgerRefusal("local ledger exists; neither local nor mirror may win automatically")
            mirror_bytes = self.read_url(mirror_url)
            mirror = self.validate_mirror_bytes(mirror_bytes)
            if expected_sha256 is None or mirror.ledger_sha256 != expected_sha256:
                raise LedgerRefusal("mirror identity does not match the externally recorded digest")
            if self.ledger_path.exists():
                raise LedgerRefusal("local ledger appeared during mirror restoration")
            restored = self.write_locked(mirror)
            if restored.canonical_bytes() != mirror_bytes:
                raise LedgerRefusal("restored canonical bytes do not match the immutable mirror")
            return restored

    def read_mirror_bytes(self, mirror: Mirror) -> bytes:
        """Read bytes from a declared mirror.

        Returns:
            Complete mirror bytes.
        """
        if mirror.url is None:
            raise LedgerRefusal("mirror URL is not recorded")
        return self.read_url(mirror.url)

    def validate_mirror_bytes(self, content: bytes) -> PortfolioLedger:
        """Validate canonical mirror bytes and their recorded identity.

        Returns:
            Reconstructed mirror ledger.
        """
        try:
            mirror = PortfolioLedger.model_validate_json(content)
        except ValueError as error:
            raise LedgerRefusal(f"mirror ledger cannot be reconstructed: {error}") from error
        if content != mirror.canonical_bytes():
            raise LedgerRefusal("mirror ledger is not canonical JSON")
        if mirror.ledger_sha256 is None or mirror.identity_sha256() != mirror.ledger_sha256:
            raise LedgerRefusal("mirror ledger digest mismatch")
        if mirror.mirror.expected_sha256 != mirror.ledger_sha256:
            raise LedgerRefusal("mirror recorded digest does not match mirrored identity")
        return mirror

    def read_url(self, url: str) -> bytes:
        """Read complete mirror bytes from a file or HTTPS URL.

        Returns:
            Complete response bytes.
        """
        try:
            with urllib.request.urlopen(url) as response:  # ruff: ignore[suspicious-url-open-usage] - URL is explicit persisted authority
                return response.read()
        except OSError as error:
            raise LedgerRefusal(f"cannot read mirror {url!r}: {error}") from error


class PortfolioLedgerService:
    """Pure transition service for one validated ledger revision."""

    def __init__(self, ledger: PortfolioLedger) -> None:
        """Bind the service to one immutable input revision.

        Args:
            ledger: Validated source revision.
        """
        self.ledger = ledger

    def acquire_reservation(self, car_id: str, reservation: Reservation, *, actor_id: str) -> PortfolioLedger:
        """Acquire exact canonical resources and advance one inventoried car.

        Args:
            car_id: Car receiving the reservation.
            reservation: Exact active reservation and receipt binding.
            actor_id: Maker acquiring its own resources.

        Returns:
            A new validated ledger revision.

        Raises:
            LedgerRefusal: When state, authority, group, paths, or exclusivity is invalid.
        """
        car = self.require_car(car_id)
        if car.state is not CarState.INVENTORIED:
            raise LedgerRefusal(f"car {car_id!r} is already reserved or past reservation")
        if actor_id != car.maker_id or reservation.owner != actor_id:
            raise LedgerRefusal("only the declared maker may acquire its reservation")
        if not car.inventory_ids:
            raise LedgerRefusal("reservation requires a frozen inventory")
        stale_inventories = [
            inventory_id
            for inventory_id in car.inventory_ids
            if self.ledger.inventories[inventory_id].revision != car.upstream_git_sha
        ]
        if stale_inventories:
            raise LedgerRefusal(f"reservation inventories are stale: {sorted(stale_inventories)}")
        inventoried_paths = {
            path.path for inventory_id in car.inventory_ids for path in self.ledger.inventories[inventory_id].paths
        }
        missing_paths = set(reservation.paths) - inventoried_paths
        if missing_paths:
            raise LedgerRefusal(f"inventory does not cover reserved paths: {sorted(missing_paths)}")
        group = self.ledger.conflict_groups.get(reservation.group)
        if group is None:
            raise LedgerRefusal(f"unknown conflict group {reservation.group!r}; aliases are not accepted")
        if reservation.state is not ReservationState.ACTIVE:
            raise LedgerRefusal("new reservation must be active")
        if sorted(reservation.paths) != sorted(group.paths):
            raise LedgerRefusal("reservation paths must exactly match the canonical conflict group")
        if reservation.id in self.ledger.reservations:
            raise LedgerRefusal(f"reservation {reservation.id!r} already exists")
        requested = set(reservation.paths)
        for existing in self.ledger.reservations.values():
            if existing.state is ReservationState.ACTIVE and requested.intersection(existing.paths):
                raise LedgerRefusal(f"resources are already reserved by {existing.id!r}")

        event = HistoryEvent(
            action="reservation-acquire",
            actor_id=actor_id,
            at=reservation.acquired_at,
            from_state=car.state,
            to_state=CarState.RESERVED,
            receipt_sha256=reservation.receipt_sha256,
        )
        updated_car = car.model_copy(
            update={
                "state": CarState.RESERVED,
                "reservation_ids": [*car.reservation_ids, reservation.id],
                "history": [*car.history, event],
            }
        )
        return self.ledger.model_copy(
            update={
                "reservations": {**self.ledger.reservations, reservation.id: reservation},
                "cars": {**self.ledger.cars, car_id: updated_car},
                "ledger_sha256": None,
            }
        )

    def record_inventory(self, car_id: str, inventory: Inventory, *, actor_id: str) -> PortfolioLedger:
        """Attach one exact current-revision inventory to an inventoried car.

        Args:
            car_id: Car receiving the inventory.
            inventory: Sorted content-addressed path set.
            actor_id: Declared maker recording its inventory facts.

        Returns:
            A new inventoried ledger revision.

        Raises:
            LedgerRefusal: When state, authority, revision, paths, or digest is invalid.
        """
        car = self.require_car(car_id)
        if car.state is not CarState.INVENTORIED:
            raise LedgerRefusal("inventory can only be recorded in INVENTORIED state")
        if actor_id != car.maker_id:
            raise LedgerRefusal("only the declared maker may record its inventory")
        if inventory.id in self.ledger.inventories:
            raise LedgerRefusal(f"inventory {inventory.id!r} already exists")
        if inventory.revision != car.upstream_git_sha:
            raise LedgerRefusal("inventory revision is stale relative to the car upstream SHA")
        path_names = [item.path for item in inventory.paths]
        if path_names != sorted(path_names) or len(path_names) != len(set(path_names)):
            raise LedgerRefusal("inventory paths must be sorted and unique")
        if any(Path(path).is_absolute() or ".." in Path(path).parts for path in path_names):
            raise LedgerRefusal("inventory paths must be tracked repository-relative paths")
        if inventory.sha256 != inventory_sha256(inventory.paths):
            raise LedgerRefusal("inventory digest does not match its exact paths")
        updated_car = car.model_copy(update={"inventory_ids": [*car.inventory_ids, inventory.id]})
        return self.ledger.model_copy(
            update={
                "inventories": {**self.ledger.inventories, inventory.id: inventory},
                "cars": {**self.ledger.cars, car_id: updated_car},
                "ledger_sha256": None,
            }
        )

    def release_reservation(
        self, car_id: str, reservation_id: str, *, actor_id: str, at: datetime, receipt_sha256: Sha256
    ) -> PortfolioLedger:
        """Release an active pre-admission reservation owned by the caller.

        Args:
            car_id: Reserved car.
            reservation_id: Active reservation id.
            actor_id: Reservation owner.
            at: Release instant.
            receipt_sha256: Immutable release receipt digest.

        Returns:
            A new inventoried ledger revision.

        Raises:
            LedgerRefusal: When authority or current state is invalid.
        """
        reservation = self.require_active_reservation(car_id, reservation_id)
        if reservation.owner != actor_id:
            raise LedgerRefusal("only the reservation owner may release it")
        return self.finish_reservation(
            car_id,
            reservation,
            actor_id=actor_id,
            at=at,
            receipt_sha256=receipt_sha256,
            state=ReservationState.RELEASED,
            action="reservation-release",
        )

    def invalidate_reservation(
        self, car_id: str, reservation_id: str, *, actor_id: str, at: datetime, receipt_sha256: Sha256
    ) -> PortfolioLedger:
        """Invalidate an active reservation under independent checker authority.

        Args:
            car_id: Reserved car.
            reservation_id: Active reservation id.
            actor_id: Independent checker.
            at: Invalidation instant.
            receipt_sha256: Immutable judgement digest.

        Returns:
            A new inventoried ledger revision.

        Raises:
            LedgerRefusal: When authority or current state is invalid.
        """
        if self.require_car(car_id).state is not CarState.RESERVED:
            raise LedgerRefusal("reservation invalidation requires RESERVED state")
        reservation = self.require_active_reservation(car_id, reservation_id)
        self.require_independent_checker(actor_id, excluded={reservation.owner})
        return self.finish_reservation(
            car_id,
            reservation,
            actor_id=actor_id,
            at=at,
            receipt_sha256=receipt_sha256,
            state=ReservationState.INVALIDATED,
            action="reservation-invalidate",
        )

    def recover_reservation(self, car_id: str, reservation_id: str, evidence: RecoveryEvidence) -> PortfolioLedger:
        """Invalidate a stale reservation only after independent recovery judgement.

        Args:
            car_id: Reserved car.
            reservation_id: Stale active reservation id.
            evidence: Process/liveness, prior-receipt, and checker evidence.

        Returns:
            A new inventoried ledger revision.

        Raises:
            LedgerRefusal: When stale-owner, receipt, evidence, or independence checks fail.
        """
        if self.require_car(car_id).state is not CarState.RESERVED:
            raise LedgerRefusal("reservation recovery requires RESERVED state")
        reservation = self.require_active_reservation(car_id, reservation_id)
        if evidence.stale_owner_id != reservation.owner:
            raise LedgerRefusal("recovery stale owner does not match the reservation owner")
        if evidence.prior_receipt_sha256 != reservation.receipt_sha256:
            raise LedgerRefusal("recovery prior receipt does not match the reservation")
        self.require_independent_checker(evidence.checker_id, excluded={reservation.owner})
        return self.finish_reservation(
            car_id,
            reservation,
            actor_id=evidence.checker_id,
            at=evidence.observed_at,
            receipt_sha256=evidence.judgement_sha256,
            state=ReservationState.INVALIDATED,
            action="reservation-recover",
        )

    def admit_implementation(
        self,
        car_id: str,
        *,
        checker_id: str,
        implementation_sha: GitSha,
        expected_base_git_sha: GitSha,
        expected_upstream_git_sha: GitSha,
        report: str,
        receipt: EvidenceReceipt,
        commands: list[CommandEvidence],
        at: datetime,
    ) -> PortfolioLedger:
        """Record maker-green implementation admission by an independent checker.

        Args:
            car_id: Reserved implementation car.
            checker_id: Maker-independent admission checker.
            implementation_sha: Exact checked implementation revision.
            expected_base_git_sha: Base identity observed by the checker.
            expected_upstream_git_sha: Upstream identity observed by the checker.
            report: Full checker report reference.
            receipt: Immutable checker judgement.
            commands: Full-output command references establishing green behavior.
            at: Admission instant.

        Returns:
            A new implementation-admitted ledger revision.

        Raises:
            LedgerRefusal: When state, SHA, authority, predecessors, or evidence is invalid.
        """
        car = self.require_car(car_id)
        if car.state is not CarState.RESERVED:
            raise LedgerRefusal("implementation admission requires RESERVED state")
        self.require_independent_checker(checker_id, excluded={car.maker_id})
        if expected_base_git_sha != car.base_git_sha:
            raise LedgerRefusal("stale base Git SHA")
        if expected_upstream_git_sha != car.upstream_git_sha:
            raise LedgerRefusal("stale upstream Git SHA")
        integrated_shas = {item.integration_sha for item in self.ledger.cars.values() if item.integration_sha}
        missing_predecessors = set(car.predecessor_shas) - integrated_shas
        if missing_predecessors:
            raise LedgerRefusal(f"missing predecessor SHAs: {sorted(missing_predecessors)}")
        if not commands or any(command.exit_code != 0 for command in commands):
            raise LedgerRefusal("maker-green command evidence is required")
        if not report or report != receipt.path:
            raise LedgerRefusal("implementation report must reference the immutable checker receipt")
        if (
            receipt.author_id != checker_id
            or receipt.verdict is not Verdict.PASSED
            or receipt.observed_revision != implementation_sha
        ):
            raise LedgerRefusal("checker receipt identity, verdict, or revision does not match admission")
        event = HistoryEvent(
            action="implementation-admit",
            actor_id=checker_id,
            at=at,
            from_state=car.state,
            to_state=CarState.IMPLEMENTATION_ADMITTED,
            receipt_sha256=receipt.sha256,
        )
        updated_car = car.model_copy(
            update={
                "state": CarState.IMPLEMENTATION_ADMITTED,
                "implementation_sha": implementation_sha,
                "implementation_checker_id": checker_id,
                "implementation_report": report,
                "commands": [*car.commands, *commands],
                "receipts": [*car.receipts, receipt],
                "history": [*car.history, event],
            }
        )
        return self.ledger.model_copy(update={"cars": {**self.ledger.cars, car_id: updated_car}, "ledger_sha256": None})

    def integrate(
        self,
        car_id: str,
        *,
        integrator_id: str,
        integration_sha: GitSha,
        expected_implementation_sha: GitSha,
        receipt: EvidenceReceipt,
        at: datetime,
    ) -> PortfolioLedger:
        """Record integration facts without granting judgement authority.

        Args:
            car_id: Implementation-admitted car.
            integrator_id: Distinct integration owner.
            integration_sha: Exact resulting integrated revision.
            expected_implementation_sha: Admitted implementation revision consumed.
            receipt: Immutable factual integration receipt.
            at: Integration instant.

        Returns:
            A new integrated ledger revision.

        Raises:
            LedgerRefusal: When state, identity, SHA, or receipt is invalid.
        """
        car = self.require_car(car_id)
        if car.state is not CarState.IMPLEMENTATION_ADMITTED:
            raise LedgerRefusal("integration requires IMPLEMENTATION_ADMITTED state")
        role = self.ledger.roles.get(integrator_id)
        if role is None or role.independence_class != "integrator":
            raise LedgerRefusal(f"actor {integrator_id!r} lacks integrator authority")
        if integrator_id in {car.maker_id, car.implementation_checker_id}:
            raise LedgerRefusal("integrator must be distinct from maker and implementation checker")
        if expected_implementation_sha != car.implementation_sha:
            raise LedgerRefusal("stale implementation Git SHA")
        if (
            receipt.author_id != integrator_id
            or receipt.verdict is not Verdict.RECORDED
            or receipt.observed_revision != integration_sha
        ):
            raise LedgerRefusal("integration receipt must record matching facts without a checker verdict")
        event = HistoryEvent(
            action="integrate",
            actor_id=integrator_id,
            at=at,
            from_state=car.state,
            to_state=CarState.INTEGRATED,
            receipt_sha256=receipt.sha256,
        )
        updated_car = car.model_copy(
            update={
                "state": CarState.INTEGRATED,
                "integration_sha": integration_sha,
                "integrator_id": integrator_id,
                "receipts": [*car.receipts, receipt],
                "history": [*car.history, event],
            }
        )
        return self.ledger.model_copy(update={"cars": {**self.ledger.cars, car_id: updated_car}, "ledger_sha256": None})

    def certify_aspect(
        self, car_id: str, *, checker_id: str, report: str, receipt: EvidenceReceipt, at: datetime
    ) -> PortfolioLedger:
        """Certify one integrated aspect aggregate after its declared consumers.

        Args:
            car_id: Integrated aggregate car.
            checker_id: Independent aspect checker.
            report: Full aspect checker report reference.
            receipt: Immutable aspect judgement.
            at: Certification instant.

        Returns:
            A new aspect-certified ledger revision.

        Raises:
            LedgerRefusal: When car kind, state, consumers, identity, or evidence is invalid.
        """
        car = self.require_car(car_id)
        if car.car_kind is not CarKind.ASPECT_AGGREGATE:
            raise LedgerRefusal("only an aspect aggregate can reach ASPECT_CERTIFIED")
        if car.state is not CarState.INTEGRATED:
            raise LedgerRefusal("aspect certification requires INTEGRATED state")
        excluded = {car.maker_id, car.implementation_checker_id, car.integrator_id}
        self.require_independent_checker(checker_id, excluded={actor for actor in excluded if actor})
        incomplete_consumers = [
            item.id
            for item in self.ledger.cars.values()
            if item.id != car.id
            and car.aspect in item.aspect_membership
            and item.state not in {CarState.INTEGRATED, CarState.ASPECT_CERTIFIED}
        ]
        if incomplete_consumers:
            raise LedgerRefusal(f"declared aspect consumers are not integrated: {sorted(incomplete_consumers)}")
        if not report or report != receipt.path:
            raise LedgerRefusal("aspect report must reference the immutable checker receipt")
        if (
            receipt.author_id != checker_id
            or receipt.verdict is not Verdict.PASSED
            or receipt.observed_revision != car.integration_sha
        ):
            raise LedgerRefusal("aspect checker receipt identity, verdict, or revision does not match")
        event = HistoryEvent(
            action="aspect-certify",
            actor_id=checker_id,
            at=at,
            from_state=car.state,
            to_state=CarState.ASPECT_CERTIFIED,
            receipt_sha256=receipt.sha256,
        )
        updated_car = car.model_copy(
            update={
                "state": CarState.ASPECT_CERTIFIED,
                "aspect_checker_id": checker_id,
                "aspect_report": report,
                "receipts": [*car.receipts, receipt],
                "history": [*car.history, event],
            }
        )
        return self.ledger.model_copy(update={"cars": {**self.ledger.cars, car_id: updated_car}, "ledger_sha256": None})

    def record_addendum(self, addendum: Addendum) -> PortfolioLedger:
        """Record independently checked exact-revision addendum evidence.

        Args:
            addendum: Immutable checked addendum.

        Returns:
            A new ledger revision containing the addendum.

        Raises:
            LedgerRefusal: When the car, checker, revision, report, or id is invalid.
        """
        if any(existing.id == addendum.id for existing in self.ledger.parent.addenda):
            raise LedgerRefusal(f"addendum {addendum.id!r} already exists")
        car = self.require_car(addendum.car_id)
        if car.state is not CarState.ASPECT_CERTIFIED:
            raise LedgerRefusal("addendum requires an ASPECT_CERTIFIED car")
        excluded = {car.maker_id, car.implementation_checker_id, car.integrator_id, car.aspect_checker_id}
        self.require_independent_checker(addendum.checker_id, excluded={actor for actor in excluded if actor})
        if addendum.revision != car.integration_sha:
            raise LedgerRefusal("addendum revision does not match the integrated car SHA")
        if addendum.report != addendum.receipt.path:
            raise LedgerRefusal("addendum report must reference its immutable receipt")
        if (
            addendum.receipt.author_id != addendum.checker_id
            or addendum.receipt.verdict is not Verdict.PASSED
            or addendum.receipt.observed_revision != addendum.revision
        ):
            raise LedgerRefusal("addendum receipt identity, verdict, or revision does not match")
        parent = self.ledger.parent.model_copy(update={"addenda": [*self.ledger.parent.addenda, addendum]})
        return self.ledger.model_copy(update={"parent": parent, "ledger_sha256": None})

    def certify_parent(
        self, *, checker_id: str, revision: GitSha, report: str, receipt: EvidenceReceipt
    ) -> PortfolioLedger:
        """Record the independent parent-only verdict at one exact revision.

        Args:
            checker_id: Independent parent checker identity.
            revision: Exact integrated portfolio revision checked.
            report: Full parent checker report reference.
            receipt: Immutable parent verdict.

        Returns:
            A parent-certified ledger revision.

        Raises:
            LedgerRefusal: When any required aggregate, addendum, authority, or evidence is invalid.
        """
        parent = self.ledger.parent
        if parent.state is not ParentState.INVENTORIED:
            raise LedgerRefusal("parent is already certified")
        role = self.ledger.roles.get(checker_id)
        if role is None or role.independence_class != "parent-checker":
            raise LedgerRefusal(f"actor {checker_id!r} lacks parent-checker authority")
        car_authorities = {
            actor
            for car in self.ledger.cars.values()
            for actor in (car.maker_id, car.implementation_checker_id, car.integrator_id, car.aspect_checker_id)
            if actor
        }
        addendum_checkers = {addendum.checker_id for addendum in parent.addenda}
        if checker_id in car_authorities | addendum_checkers:
            raise LedgerRefusal("parent checker must be independent from all portfolio authorities")
        declared_required = {car.id for car in self.ledger.cars.values() if car.required_for_parent}
        listed_required = set(parent.required_car_ids)
        if listed_required != declared_required or len(parent.required_car_ids) != len(listed_required):
            raise LedgerRefusal("parent required car set does not exactly match cars marked required")
        required = [self.require_car(car_id) for car_id in parent.required_car_ids]
        invalid = [
            car.id
            for car in required
            if not car.required_for_parent
            or car.car_kind is not CarKind.ASPECT_AGGREGATE
            or car.state is not CarState.ASPECT_CERTIFIED
        ]
        if invalid:
            raise LedgerRefusal(f"required parent cars are not certified aggregates: {sorted(invalid)}")
        present_addenda = {addendum.id for addendum in parent.addenda}
        missing_addenda = set(parent.required_addendum_ids) - present_addenda
        if missing_addenda:
            raise LedgerRefusal(f"required parent addenda are missing: {sorted(missing_addenda)}")
        if not report or report != receipt.path:
            raise LedgerRefusal("parent report must reference the immutable checker receipt")
        if (
            receipt.author_id != checker_id
            or receipt.verdict is not Verdict.PASSED
            or receipt.observed_revision != revision
        ):
            raise LedgerRefusal("parent receipt identity, verdict, or revision does not match")
        certified = parent.model_copy(
            update={
                "state": ParentState.PARENT_CERTIFIED,
                "checker_id": checker_id,
                "revision": revision,
                "report": report,
                "receipt": receipt,
            }
        )
        return self.ledger.model_copy(update={"parent": certified, "ledger_sha256": None})

    def finish_reservation(
        self,
        car_id: str,
        reservation: Reservation,
        *,
        actor_id: str,
        at: datetime,
        receipt_sha256: Sha256,
        state: ReservationState,
        action: str,
    ) -> PortfolioLedger:
        """Apply a validated pre-admission reservation conclusion.

        Returns:
            Updated ledger.
        """
        car = self.require_car(car_id)
        target_state = (
            car.state
            if state is ReservationState.RELEASED and car.state is not CarState.RESERVED
            else CarState.INVENTORIED
        )
        updated_reservation = reservation.model_copy(
            update={
                "state": state,
                "released_at": at if state is ReservationState.RELEASED else None,
                "invalidated_at": at if state is ReservationState.INVALIDATED else None,
            }
        )
        event = HistoryEvent(
            action=action,
            actor_id=actor_id,
            at=at,
            from_state=car.state,
            to_state=target_state,
            receipt_sha256=receipt_sha256,
        )
        updated_car = car.model_copy(
            update={
                "state": target_state,
                "reservation_ids": [item for item in car.reservation_ids if item != reservation.id],
                "history": [*car.history, event],
            }
        )
        return self.ledger.model_copy(
            update={
                "reservations": {**self.ledger.reservations, reservation.id: updated_reservation},
                "cars": {**self.ledger.cars, car_id: updated_car},
                "ledger_sha256": None,
            }
        )

    def require_active_reservation(self, car_id: str, reservation_id: str) -> Reservation:
        """Return an active reservation attached to a reserved car."""
        car = self.require_car(car_id)
        if car.state is CarState.INVENTORIED or reservation_id not in car.reservation_ids:
            raise LedgerRefusal("reservation conclusion requires an attached active reservation")
        reservation = self.ledger.reservations.get(reservation_id)
        if reservation is None or reservation.state is not ReservationState.ACTIVE:
            raise LedgerRefusal(f"reservation {reservation_id!r} is not active")
        return reservation

    def require_independent_checker(self, actor_id: str, *, excluded: set[str]) -> Role:
        """Require a checker identity distinct from all excluded actors.

        Returns:
            Validated checker role.
        """
        role = self.ledger.roles.get(actor_id)
        if role is None or role.independence_class != "checker":
            raise LedgerRefusal(f"actor {actor_id!r} is not an independent checker")
        if actor_id in excluded:
            raise LedgerRefusal(f"checker {actor_id!r} collides with an excluded authority")
        return role

    def require_car(self, car_id: str) -> Car:
        """Return a declared car or refuse an undefined id.

        Args:
            car_id: Exact car id.

        Returns:
            Declared car.

        Raises:
            LedgerRefusal: When the car is undefined.
        """
        car = self.ledger.cars.get(car_id)
        if car is None:
            raise LedgerRefusal(f"undefined car {car_id!r}")
        return car
