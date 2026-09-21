"""Contract tests for the canonical portfolio merge ledger."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import Self

import pytest
from dh_core.portfolio_ledger import (
    CANONICAL_CONFLICT_GROUP_IDS,
    Addendum,
    Car,
    CarKind,
    CarState,
    CommandEvidence,
    ConflictGroup,
    CorrectionRow,
    EvidenceReceipt,
    HistoryEvent,
    Inventory,
    InventoryPath,
    LedgerRefusal,
    Mirror,
    Parent,
    ParentState,
    PortfolioLedger,
    PortfolioLedgerRuntime,
    PortfolioLedgerService,
    RecoveryEvidence,
    Reservation,
    ReservationState,
    Role,
    TrackerManifest,
    _LedgerStore as LedgerStore,
    file_path_to_uri,
    file_uri_to_path,
    inventory_sha256,
)

SHA = "a" * 64
NOW = datetime(2026, 9, 21, tzinfo=UTC)


def inventory_record() -> Inventory:
    """Build one canonical frozen inventory."""
    paths = [InventoryPath(path="plugins/development-harness/dh_core/portfolio_ledger.py", git_blob=SHA, sha256=SHA)]
    digest = hashlib.sha256(
        json.dumps([item.model_dump(mode="json") for item in paths], separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    return Inventory(id="inventory-a6-g0", revision=SHA, paths=paths, sha256=digest)


def conflict_group_registry() -> dict[str, ConflictGroup]:
    """Build the complete certified conflict-group vocabulary."""
    groups = {group_id: ConflictGroup(id=group_id, paths=[]) for group_id in CANONICAL_CONFLICT_GROUP_IDS}
    groups["CG-PORTFOLIO-LEDGER"] = ConflictGroup(
        id="CG-PORTFOLIO-LEDGER", paths=["plugins/development-harness/dh_core/portfolio_ledger.py"]
    )
    return groups


def minimum_ledger() -> PortfolioLedger:
    """Build the smallest portfolio that satisfies the persisted schema."""
    return PortfolioLedger(
        portfolio_issue=3620,
        tracker_manifest=TrackerManifest(
            path=".tmp/reports/runtime-integrity-tracker-manifest.md", sha256=SHA, observed_at=NOW
        ),
        correction_rows={
            f"R{number:02d}": CorrectionRow(
                owner="maker", artifact=f"receipt-{number}.json", sha256=SHA, reviewer="checker"
            )
            for number in range(1, 22)
        },
        roles={
            "maker": Role(id="maker", session="session-maker", independence_class="maker"),
            "checker": Role(id="checker", session="session-checker", independence_class="checker"),
            "checker-2": Role(id="checker-2", session="session-checker-2", independence_class="checker"),
            "checker-3": Role(id="checker-3", session="session-checker-3", independence_class="checker"),
            "integrator": Role(id="integrator", session="session-integrator", independence_class="integrator"),
            "parent-checker": Role(id="parent-checker", session="session-parent", independence_class="parent-checker"),
        },
        conflict_groups=conflict_group_registry(),
        cars={
            "A6-G0": Car(
                id="A6-G0",
                issue=3679,
                aspect="A6",
                car_kind=CarKind.IMPLEMENTATION,
                required_for_parent=False,
                aspect_membership=["A6"],
                state=CarState.INVENTORIED,
                base_git_sha=SHA,
                upstream_git_sha=SHA,
                maker_id="maker",
                inventory_ids=["inventory-a6-g0"],
                history=[
                    HistoryEvent(
                        action="inventory",
                        actor_id="maker",
                        at=NOW,
                        from_state="INVENTORIED",
                        to_state="INVENTORIED",
                        inventory_ids=["inventory-a6-g0"],
                        reservation_id=None,
                        receipt_path="plugins/development-harness/dh_core/portfolio_ledger.py",
                        receipt_sha256=SHA,
                    )
                ],
            )
        },
        inventories={"inventory-a6-g0": inventory_record()},
        parent=Parent(state=ParentState.INVENTORIED, required_car_ids=[]),
        mirror=Mirror(),
    )


def materialized_ledger(root: Path) -> PortfolioLedger:
    """Build a minimum ledger whose complete evidence bytes exist below root."""
    ledger = minimum_ledger()
    tracker_bytes = b"runtime-integrity tracker\n"
    (root / "tracker.md").write_bytes(tracker_bytes)
    corrections: dict[str, CorrectionRow] = {}
    for row_id, row in ledger.correction_rows.items():
        content = json.dumps({"row": row_id, "verdict": "PASS"}, separators=(",", ":")).encode()
        path = f"corrections/{row_id}.json"
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_bytes(content)
        corrections[row_id] = row.model_copy(update={"artifact": path, "sha256": hashlib.sha256(content).hexdigest()})
    source_bytes = b'"""portfolio ledger source evidence"""\n'
    source_path = "plugins/development-harness/dh_core/portfolio_ledger.py"
    (root / source_path).parent.mkdir(parents=True, exist_ok=True)
    (root / source_path).write_bytes(source_bytes)
    path = InventoryPath(path=source_path, git_blob=SHA, sha256=hashlib.sha256(source_bytes).hexdigest())
    inventory = Inventory(id="inventory-a6-g0", revision=SHA, paths=[path], sha256=inventory_sha256([path]))
    car = ledger.cars["A6-G0"]
    history = [
        car.history[0].model_copy(
            update={"receipt_path": source_path, "receipt_sha256": path.sha256, "inventory_ids": [inventory.id]}
        )
    ]
    return ledger.model_copy(
        update={
            "tracker_manifest": ledger.tracker_manifest.model_copy(
                update={"path": "tracker.md", "sha256": hashlib.sha256(tracker_bytes).hexdigest()}
            ),
            "correction_rows": corrections,
            "inventories": {inventory.id: inventory},
            "cars": {car.id: car.model_copy(update={"history": history})},
        }
    )


def admitted_ledger() -> PortfolioLedger:
    """Build one implementation-admitted car through public transitions."""
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path=".tmp/reports/runtime-integrity-merge-train-ledger.lock",
        acquired_at=NOW,
        receipt_path="evidence/reservation.json",
        receipt_sha256=SHA,
    )
    reserved = PortfolioLedgerService(minimum_ledger()).acquire_reservation("A6-G0", reservation, actor_id="maker")
    receipt = EvidenceReceipt(
        path="evidence/admission.json", sha256=SHA, author_id="checker", verdict="PASS", observed_revision=SHA
    )
    return PortfolioLedgerService(reserved).admit_implementation(
        "A6-G0",
        checker_id="checker",
        implementation_sha=SHA,
        expected_base_git_sha=SHA,
        expected_upstream_git_sha=SHA,
        report=receipt.path,
        receipt=receipt,
        commands=[
            CommandEvidence(
                argv=["uv", "run", "pytest"], exit_code=0, output_path="evidence/pytest.txt", output_sha256=SHA
            )
        ],
        at=NOW,
    )


def integrated_ledger(*, car_kind: CarKind = CarKind.IMPLEMENTATION) -> PortfolioLedger:
    """Build one integrated car through public transitions."""
    admitted = admitted_ledger()
    car = admitted.cars["A6-G0"].model_copy(update={"car_kind": car_kind})
    admitted = admitted.model_copy(update={"cars": {"A6-G0": car}})
    receipt = EvidenceReceipt(
        path="evidence/integration.json",
        sha256=SHA,
        author_id="integrator",
        verdict="RECORDED",
        observed_revision="b" * 64,
    )
    return PortfolioLedgerService(admitted).integrate(
        "A6-G0",
        integrator_id="integrator",
        integration_sha="b" * 64,
        expected_implementation_sha=SHA,
        receipt=receipt,
        at=NOW,
    )


def test_persisted_schema_reconstructs_byte_identically() -> None:
    ledger = minimum_ledger()

    encoded = ledger.canonical_json()
    reconstructed = PortfolioLedger.model_validate_json(encoded)

    assert reconstructed.canonical_json() == encoded


def test_reconstructed_correction_rows_require_passed_independent_review() -> None:
    payload = minimum_ledger().model_dump(mode="json")
    payload["correction_rows"]["R01"].update(owner="same", reviewer="same", verdict="REFUSED")

    with pytest.raises(ValueError, match="passed independent review"):
        PortfolioLedger.model_validate(payload)


def test_persisted_reconstruction_rejects_skipped_states_and_car_level_parent_certification() -> None:
    payload = minimum_ledger().model_dump(mode="json")
    payload["cars"]["A6-G0"]["state"] = "IMPLEMENTATION_ADMITTED"
    with pytest.raises(ValueError, match="IMPLEMENTATION_ADMITTED"):
        PortfolioLedger.model_validate(payload)

    payload["cars"]["A6-G0"]["state"] = "PARENT_CERTIFIED"
    with pytest.raises(ValueError, match="PARENT_CERTIFIED"):
        PortfolioLedger.model_validate(payload)


def test_persisted_parent_certification_requires_complete_verdict_evidence() -> None:
    payload = minimum_ledger().model_dump(mode="json")
    payload["parent"]["state"] = "PARENT_CERTIFIED"

    with pytest.raises(ValueError, match="parent certification evidence"):
        PortfolioLedger.model_validate(payload)

    receipt = EvidenceReceipt(
        path="evidence/parent.json", sha256=SHA, author_id="parent-checker", verdict="PASS", observed_revision=SHA
    )
    payload["parent"].update(
        checker_id="parent-checker", revision=SHA, report=receipt.path, receipt=receipt.model_dump(mode="json")
    )
    with pytest.raises(ValueError, match="certified parent requires"):
        PortfolioLedger.model_validate(payload)


def test_reconstructed_car_enforces_transition_equivalent_evidence_and_independence() -> None:
    aggregate = integrated_ledger(car_kind=CarKind.ASPECT_AGGREGATE)
    receipt = EvidenceReceipt(
        path="evidence/aspect.json", sha256=SHA, author_id="checker-2", verdict="PASS", observed_revision="b" * 64
    )
    certified = PortfolioLedgerService(aggregate).certify_aspect(
        "A6-G0", checker_id="checker-2", report=receipt.path, receipt=receipt, at=NOW
    )
    payload = certified.model_dump(mode="json")
    car = payload["cars"]["A6-G0"]
    car["implementation_checker_id"] = "maker"
    car["integrator_id"] = "maker"
    car["aspect_checker_id"] = "maker"
    car["commands"][0]["exit_code"] = 1
    car["receipts"] = []

    with pytest.raises(ValueError, match="transition-equivalent"):
        PortfolioLedger.model_validate(payload)


def test_reconstructed_integrated_car_requires_legal_history_chain() -> None:
    payload = integrated_ledger().model_dump(mode="json")
    payload["cars"]["A6-G0"]["history"] = []
    with pytest.raises(ValueError, match=r"history chain|inventory pointer"):
        PortfolioLedger.model_validate(payload)


def test_reconstruction_rejects_malformed_sha_missing_predecessor_and_unintegrated_consumer() -> None:
    malformed_sha = minimum_ledger().model_dump(mode="json")
    malformed_sha["cars"]["A6-G0"]["base_git_sha"] = "a" * 41
    with pytest.raises(ValueError, match="String should match pattern"):
        PortfolioLedger.model_validate(malformed_sha)

    missing_predecessor = admitted_ledger().model_dump(mode="json")
    missing_predecessor["cars"]["A6-G0"]["predecessor_shas"] = ["c" * 64]
    with pytest.raises(ValueError, match="absent predecessor"):
        PortfolioLedger.model_validate(missing_predecessor)

    aggregate = integrated_ledger(car_kind=CarKind.ASPECT_AGGREGATE)
    aspect_receipt = EvidenceReceipt(
        path="evidence/aspect.json", sha256=SHA, author_id="checker-2", verdict="PASS", observed_revision="b" * 64
    )
    certified = PortfolioLedgerService(aggregate).certify_aspect(
        "A6-G0", checker_id="checker-2", report=aspect_receipt.path, receipt=aspect_receipt, at=NOW
    )
    consumer = minimum_ledger().cars["A6-G0"].model_copy(update={"id": "UNINTEGRATED", "issue": 9996})
    payload = certified.model_copy(update={"cars": {**certified.cars, consumer.id: consumer}}).model_dump(mode="json")
    with pytest.raises(ValueError, match="consumer is not integrated"):
        PortfolioLedger.model_validate(payload)


def test_inventory_records_only_sorted_exact_content_at_the_current_revision() -> None:
    ledger = minimum_ledger()
    car = ledger.cars["A6-G0"].model_copy(update={"inventory_ids": []})
    ledger = ledger.model_copy(update={"inventories": {}, "cars": {"A6-G0": car}})
    inventory = inventory_record()

    recorded = PortfolioLedgerService(ledger).record_inventory("A6-G0", inventory, actor_id="maker")

    assert recorded.cars["A6-G0"].inventory_ids == [inventory.id]
    with pytest.raises(LedgerRefusal, match="digest"):
        PortfolioLedgerService(ledger).record_inventory(
            "A6-G0", inventory.model_copy(update={"sha256": "b" * 64}), actor_id="maker"
        )


def test_persisted_registry_rejects_a_self_declared_conflict_group_alias() -> None:
    ledger = minimum_ledger()
    groups = {**ledger.conflict_groups, "CG-LEDGER": ConflictGroup(id="CG-LEDGER", paths=["invented/alias.py"])}

    with pytest.raises(ValueError, match="unknown conflict groups"):
        PortfolioLedger.model_validate({**ledger.model_dump(mode="python"), "conflict_groups": groups})
    with pytest.raises(ValueError, match="complete canonical conflict-group registry"):
        PortfolioLedger.model_validate({**ledger.model_dump(mode="python"), "conflict_groups": {}})


def test_reservation_acquire_is_exclusive_and_advances_the_car() -> None:
    ledger = minimum_ledger()
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path=".tmp/reports/runtime-integrity-merge-train-ledger.lock",
        acquired_at=NOW,
        receipt_path="evidence/reservation.json",
        receipt_sha256=SHA,
    )
    service = PortfolioLedgerService(ledger)

    updated = service.acquire_reservation("A6-G0", reservation, actor_id="maker")

    assert updated.cars["A6-G0"].state is CarState.RESERVED
    assert updated.cars["A6-G0"].reservation_ids == [reservation.id]
    with pytest.raises(LedgerRefusal, match="already reserved"):
        PortfolioLedgerService(updated).acquire_reservation("A6-G0", reservation, actor_id="maker")


def test_reservation_requires_inventory_coverage_of_every_reserved_path() -> None:
    ledger = minimum_ledger()
    unrelated = InventoryPath(path="unrelated.py", git_blob=SHA, sha256=SHA)
    inventory = Inventory(id="inventory-a6-g0", revision=SHA, paths=[unrelated], sha256=inventory_sha256([unrelated]))
    ledger = ledger.model_copy(update={"inventories": {inventory.id: inventory}})
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        owner_process_id=os.getpid(),
        state=ReservationState.ACTIVE,
        lock_path="ledger.lock",
        acquired_at=NOW,
        receipt_path="evidence/reservation.json",
        receipt_sha256=SHA,
    )

    with pytest.raises(LedgerRefusal, match="inventory does not cover"):
        PortfolioLedgerService(ledger).acquire_reservation("A6-G0", reservation, actor_id="maker")


def test_reservation_rejects_an_inventoried_writable_path_left_unreserved() -> None:
    ledger = minimum_ledger()
    extra = InventoryPath(path="unreserved-writable.py", git_blob=SHA, sha256=SHA)
    inventory = inventory_record().model_copy(
        update={
            "paths": [*inventory_record().paths, extra],
            "sha256": inventory_sha256([*inventory_record().paths, extra]),
        }
    )
    groups = dict(ledger.conflict_groups)
    groups["CG-CORE-OPS"] = ConflictGroup(id="CG-CORE-OPS", paths=[extra.path])
    ledger = ledger.model_copy(update={"inventories": {inventory.id: inventory}, "conflict_groups": groups})
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path="ledger.lock",
        acquired_at=NOW,
        receipt_sha256=SHA,
    )

    with pytest.raises(LedgerRefusal, match="inventoried writable paths must exactly match"):
        PortfolioLedgerService(ledger).acquire_reservation("A6-G0", reservation, actor_id="maker")


def test_empty_inventory_group_and_reservation_cannot_reach_reserved() -> None:
    ledger = minimum_ledger()
    empty_inventory = Inventory(id="inventory-a6-g0", revision=SHA, paths=[], sha256=inventory_sha256([]))
    groups = dict(ledger.conflict_groups)
    groups["CG-PORTFOLIO-LEDGER"] = ConflictGroup(id="CG-PORTFOLIO-LEDGER", paths=[])
    ledger = ledger.model_copy(update={"inventories": {empty_inventory.id: empty_inventory}, "conflict_groups": groups})
    reservation = Reservation(
        id="empty-reservation",
        group="CG-PORTFOLIO-LEDGER",
        paths=[],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path="ledger.lock",
        acquired_at=NOW,
        receipt_path="evidence/empty-reservation.json",
        receipt_sha256=SHA,
    )

    with pytest.raises(LedgerRefusal, match="non-empty"):
        PortfolioLedgerService(ledger).acquire_reservation("A6-G0", reservation, actor_id="maker")


def test_reconstructed_reserved_car_requires_active_owned_exclusive_reservation() -> None:
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path="ledger.lock",
        acquired_at=NOW,
        receipt_sha256=SHA,
    )
    acquired = PortfolioLedgerService(minimum_ledger()).acquire_reservation("A6-G0", reservation, actor_id="maker")
    payload = acquired.model_dump(mode="json")
    payload["reservations"][reservation.id]["state"] = "released"

    with pytest.raises(ValueError, match=r"active owned exclusive reservation|terminal timestamps|terminal receipt"):
        PortfolioLedger.model_validate(payload)


def test_reservation_release_and_invalidate_return_to_inventory() -> None:
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path=".tmp/reports/runtime-integrity-merge-train-ledger.lock",
        acquired_at=NOW,
        receipt_path="evidence/reservation.json",
        receipt_sha256=SHA,
    )
    acquired = PortfolioLedgerService(minimum_ledger()).acquire_reservation("A6-G0", reservation, actor_id="maker")

    released = PortfolioLedgerService(acquired).release_reservation(
        "A6-G0", reservation.id, actor_id="maker", at=NOW, receipt_sha256=SHA
    )
    assert released.reservations[reservation.id].state is ReservationState.RELEASED
    assert released.cars["A6-G0"].state is CarState.INVENTORIED

    second = reservation.model_copy(update={"id": "reservation-second"})
    reacquired = PortfolioLedgerService(released).acquire_reservation("A6-G0", second, actor_id="maker")
    invalidated = PortfolioLedgerService(reacquired).invalidate_reservation(
        "A6-G0", second.id, actor_id="checker", at=NOW, receipt_sha256=SHA
    )
    assert invalidated.reservations[second.id].state is ReservationState.INVALIDATED
    assert invalidated.cars["A6-G0"].state is CarState.INVENTORIED


def test_release_allows_second_reservation_cycle_with_history_reconstruction() -> None:
    first = Reservation(
        id="cycle-one",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path="ledger.lock",
        acquired_at=NOW,
        receipt_path="evidence/cycle-one.json",
        receipt_sha256=SHA,
    )
    reserved = PortfolioLedgerService(minimum_ledger()).acquire_reservation("A6-G0", first, actor_id="maker")
    released = PortfolioLedgerService(reserved).release_reservation(
        "A6-G0", first.id, actor_id="maker", at=NOW, receipt_path="evidence/release.json", receipt_sha256=SHA
    )
    second = first.model_copy(update={"id": "cycle-two"})
    reserved_again = PortfolioLedgerService(released).acquire_reservation("A6-G0", second, actor_id="maker")
    reconstructed = PortfolioLedger.model_validate(reserved_again.model_dump(mode="python"))
    assert reconstructed.cars["A6-G0"].state is CarState.RESERVED
    assert reconstructed.cars["A6-G0"].reservation_ids == [second.id]
    assert set(reconstructed.reservations) == {first.id, second.id}


def test_recovery_verifies_liveness_and_judgement_bytes_and_rejects_live_owner(tmp_path: Path) -> None:
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path="ledger.lock",
        acquired_at=NOW,
        receipt_path="evidence/reservation.json",
        receipt_sha256=SHA,
    )
    acquired = PortfolioLedgerService(minimum_ledger()).acquire_reservation("A6-G0", reservation, actor_id="maker")
    owner_pid = acquired.reservations[reservation.id].owner_process_id
    assert owner_pid is not None
    liveness = json.dumps({"pid": owner_pid, "alive": True}, separators=(",", ":")).encode()
    judgement = b'{"verdict":"PASS","reason":"owner confirmed stale"}'
    (tmp_path / "liveness.json").write_bytes(liveness)
    (tmp_path / "judgement.json").write_bytes(judgement)
    evidence = RecoveryEvidence(
        stale_owner_id="maker",
        process_id=owner_pid,
        liveness_output_path="liveness.json",
        liveness_output_sha256=hashlib.sha256(liveness).hexdigest(),
        liveness_pid=owner_pid,
        liveness_alive=False,
        prior_receipt_sha256=SHA,
        checker_id="checker",
        judgement_path="judgement.json",
        judgement_sha256=hashlib.sha256(judgement).hexdigest(),
        judgement_checker_id="checker",
        judgement_verdict="PASS",
        observed_at=NOW,
    )

    with pytest.raises(LedgerRefusal, match="still live"):
        PortfolioLedgerService(acquired, evidence_root=tmp_path).recover_reservation("A6-G0", reservation.id, evidence)

    dead_pid = 99_999_999
    dead_liveness = json.dumps({"pid": dead_pid, "alive": False}, separators=(",", ":")).encode()
    passed_judgement = json.dumps(
        {"verdict": "PASS", "checker_id": "checker", "reason": "owner confirmed stale"}, separators=(",", ":")
    ).encode()
    (tmp_path / "liveness.json").write_bytes(dead_liveness)
    (tmp_path / "judgement.json").write_bytes(passed_judgement)
    dead_reservation = acquired.reservations[reservation.id].model_copy(update={"owner_process_id": dead_pid})
    acquired_dead = acquired.model_copy(update={"reservations": {reservation.id: dead_reservation}})
    recovered = PortfolioLedgerService(acquired_dead, evidence_root=tmp_path).recover_reservation(
        "A6-G0",
        reservation.id,
        evidence.model_copy(
            update={
                "process_id": dead_pid,
                "liveness_pid": dead_pid,
                "liveness_output_sha256": hashlib.sha256(dead_liveness).hexdigest(),
                "judgement_sha256": hashlib.sha256(passed_judgement).hexdigest(),
            }
        ),
    )
    assert recovered.reservations[reservation.id].state is ReservationState.INVALIDATED
    assert recovered.cars["A6-G0"].state is CarState.INVENTORIED

    hostile = recovered.model_dump(mode="json")
    hostile_recovery = hostile["reservations"][reservation.id]["recovery_evidence"]
    hostile_recovery["process_id"] = dead_pid - 1
    hostile_recovery["observed_at"] = "2026-09-21T00:00:01Z"
    with pytest.raises(ValueError, match=r"liveness claims|observed_at"):
        PortfolioLedger.model_validate(hostile)

    for field, value in (("liveness_alive", True), ("judgement_checker_id", "maker"), ("judgement_verdict", "REFUSED")):
        hostile = recovered.model_dump(mode="json")
        hostile["reservations"][reservation.id]["recovery_evidence"][field] = value
        with pytest.raises(ValueError, match=r"recovery|Input should be"):
            PortfolioLedger.model_validate(hostile)

    wrong_owner_process = recovered.model_dump(mode="json")
    recovery_payload = wrong_owner_process["reservations"][reservation.id]["recovery_evidence"]
    recovery_payload["process_id"] = dead_pid - 1
    recovery_payload["liveness_pid"] = dead_pid - 1
    with pytest.raises(ValueError, match="owner process"):
        PortfolioLedger.model_validate(wrong_owner_process)


def test_invalidation_replay_rejects_stale_inventory_and_recover_without_evidence() -> None:
    reservation = Reservation(
        id="r1",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path="ledger.lock",
        acquired_at=NOW,
        receipt_path="evidence/r1.json",
        receipt_sha256=SHA,
    )
    reserved = PortfolioLedgerService(minimum_ledger()).acquire_reservation("A6-G0", reservation, actor_id="maker")
    invalidated = PortfolioLedgerService(reserved).invalidate_reservation(
        "A6-G0", reservation.id, actor_id="checker", at=NOW, receipt_path="evidence/end.json", receipt_sha256=SHA
    )
    stale = invalidated.model_dump(mode="json")
    stale["cars"]["A6-G0"]["inventory_ids"] = ["inventory-a6-g0"]
    with pytest.raises(ValueError, match="inventory projection"):
        PortfolioLedger.model_validate(stale)

    missing_recovery = invalidated.model_dump(mode="json")
    missing_recovery["cars"]["A6-G0"]["history"][-1]["action"] = "reservation-recover"
    with pytest.raises(ValueError, match=r"recovery event lacks|lacks matching car history"):
        PortfolioLedger.model_validate(missing_recovery)


def test_windows_liveness_probe_never_calls_destructive_os_kill(monkeypatch: pytest.MonkeyPatch) -> None:
    service = PortfolioLedgerService(minimum_ledger())
    monkeypatch.setattr("dh_core.portfolio_ledger.os.name", "nt")
    monkeypatch.setattr(
        "dh_core.portfolio_ledger.os.kill", lambda *_args: pytest.fail("os.kill is destructive on Windows")
    )
    monkeypatch.setattr(service, "_windows_process_is_alive", lambda _pid: True)
    assert service.process_is_alive(1234)


def test_release_after_integration_preserves_the_integrated_car_state() -> None:
    integrated = integrated_ledger()

    released = PortfolioLedgerService(integrated).release_reservation(
        "A6-G0", "reservation-a6-g0", actor_id="maker", at=NOW, receipt_sha256=SHA
    )

    assert released.reservations["reservation-a6-g0"].state is ReservationState.RELEASED
    assert released.cars["A6-G0"].state is CarState.INTEGRATED


def test_invalidation_cannot_rewind_a_post_admission_car() -> None:
    integrated = integrated_ledger()

    with pytest.raises(LedgerRefusal, match="RESERVED"):
        PortfolioLedgerService(integrated).invalidate_reservation(
            "A6-G0", "reservation-a6-g0", actor_id="checker-2", at=NOW, receipt_sha256=SHA
        )


def test_implementation_admission_requires_green_evidence_fresh_shas_and_independent_checker() -> None:
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path=".tmp/reports/runtime-integrity-merge-train-ledger.lock",
        acquired_at=NOW,
        receipt_path="evidence/reservation.json",
        receipt_sha256=SHA,
    )
    reserved = PortfolioLedgerService(minimum_ledger()).acquire_reservation("A6-G0", reservation, actor_id="maker")
    command = CommandEvidence(
        argv=["uv", "run", "pytest"], exit_code=0, output_path="evidence/pytest.txt", output_sha256=SHA
    )
    receipt = EvidenceReceipt(
        path="evidence/admission.json", sha256=SHA, author_id="checker", verdict="PASS", observed_revision=SHA
    )

    admitted = PortfolioLedgerService(reserved).admit_implementation(
        "A6-G0",
        checker_id="checker",
        implementation_sha=SHA,
        expected_base_git_sha=SHA,
        expected_upstream_git_sha=SHA,
        report=receipt.path,
        receipt=receipt,
        commands=[command],
        at=NOW,
    )

    assert admitted.cars["A6-G0"].state is CarState.IMPLEMENTATION_ADMITTED
    assert admitted.cars["A6-G0"].implementation_checker_id == "checker"
    with pytest.raises(LedgerRefusal, match="checker"):
        PortfolioLedgerService(reserved).admit_implementation(
            "A6-G0",
            checker_id="maker",
            implementation_sha=SHA,
            expected_base_git_sha=SHA,
            expected_upstream_git_sha=SHA,
            report=receipt.path,
            receipt=receipt.model_copy(update={"author_id": "maker"}),
            commands=[command],
            at=NOW,
        )
    with pytest.raises(LedgerRefusal, match="stale base"):
        PortfolioLedgerService(reserved).admit_implementation(
            "A6-G0",
            checker_id="checker",
            implementation_sha=SHA,
            expected_base_git_sha="b" * 64,
            expected_upstream_git_sha=SHA,
            report=receipt.path,
            receipt=receipt,
            commands=[command],
            at=NOW,
        )
    with pytest.raises(LedgerRefusal, match="green command evidence"):
        PortfolioLedgerService(reserved).admit_implementation(
            "A6-G0",
            checker_id="checker",
            implementation_sha=SHA,
            expected_base_git_sha=SHA,
            expected_upstream_git_sha=SHA,
            report=receipt.path,
            receipt=receipt,
            commands=[],
            at=NOW,
        )


def test_implementation_admission_revalidates_active_reservation_coverage() -> None:
    reserved = admitted_ledger()
    reserved_car = reserved.cars["A6-G0"].model_copy(
        update={
            "state": CarState.RESERVED,
            "implementation_sha": None,
            "implementation_checker_id": None,
            "implementation_report": None,
            "commands": [],
            "receipts": [],
            "history": reserved.cars["A6-G0"].history[:1],
        }
    )
    unrelated = InventoryPath(path="unrelated.py", git_blob=SHA, sha256=SHA)
    inventory = Inventory(id="inventory-a6-g0", revision=SHA, paths=[unrelated], sha256=inventory_sha256([unrelated]))
    malformed = reserved.model_copy(
        update={"cars": {reserved_car.id: reserved_car}, "inventories": {inventory.id: inventory}}
    )
    receipt = EvidenceReceipt(
        path="evidence/admission.json", sha256=SHA, author_id="checker", verdict="PASS", observed_revision=SHA
    )

    with pytest.raises(LedgerRefusal, match="active reservation coverage"):
        PortfolioLedgerService(malformed).admit_implementation(
            "A6-G0",
            checker_id="checker",
            implementation_sha=SHA,
            expected_base_git_sha=SHA,
            expected_upstream_git_sha=SHA,
            report=receipt.path,
            receipt=receipt,
            commands=[
                CommandEvidence(
                    argv=["uv", "run", "pytest"], exit_code=0, output_path="evidence/pytest.txt", output_sha256=SHA
                )
            ],
            at=NOW,
        )


def test_implementation_admission_requires_real_hashed_evidence_and_session_independence(tmp_path: Path) -> None:
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path="ledger.lock",
        acquired_at=NOW,
        receipt_path="evidence/reservation.json",
        receipt_sha256=SHA,
    )
    reserved = PortfolioLedgerService(minimum_ledger()).acquire_reservation("A6-G0", reservation, actor_id="maker")
    independent_reserved = reserved
    roles = dict(reserved.roles)
    roles["checker"] = roles["checker"].model_copy(update={"session": roles["maker"].session})
    reserved = reserved.model_copy(update={"roles": roles})
    receipt = EvidenceReceipt(
        path="missing-admission.json", sha256=SHA, author_id="checker", verdict="PASS", observed_revision=SHA
    )

    with pytest.raises(LedgerRefusal, match=r"evidence|session"):
        PortfolioLedgerService(reserved, evidence_root=tmp_path).admit_implementation(
            "A6-G0",
            checker_id="checker",
            implementation_sha=SHA,
            expected_base_git_sha=SHA,
            expected_upstream_git_sha=SHA,
            report=receipt.path,
            receipt=receipt,
            commands=[
                CommandEvidence(
                    argv=["uv", "run", "pytest"], exit_code=0, output_path="missing-output.txt", output_sha256=SHA
                )
            ],
            at=NOW,
        )
    with pytest.raises(LedgerRefusal, match="does not exist"):
        PortfolioLedgerService(independent_reserved, evidence_root=tmp_path).admit_implementation(
            "A6-G0",
            checker_id="checker",
            implementation_sha=SHA,
            expected_base_git_sha=SHA,
            expected_upstream_git_sha=SHA,
            report=receipt.path,
            receipt=receipt,
            commands=[
                CommandEvidence(
                    argv=["uv", "run", "pytest"], exit_code=0, output_path="missing-output.txt", output_sha256=SHA
                )
            ],
            at=NOW,
        )

    report_bytes = b'{"checker":"checker","verdict":"PASS"}'
    output_bytes = b"29 passed\n"
    (tmp_path / "admission.json").write_bytes(report_bytes)
    (tmp_path / "pytest.txt").write_bytes(output_bytes)
    valid_receipt = receipt.model_copy(
        update={"path": "admission.json", "sha256": hashlib.sha256(report_bytes).hexdigest()}
    )
    admitted = PortfolioLedgerService(independent_reserved, evidence_root=tmp_path).admit_implementation(
        "A6-G0",
        checker_id="checker",
        implementation_sha=SHA,
        expected_base_git_sha=SHA,
        expected_upstream_git_sha=SHA,
        report=valid_receipt.path,
        receipt=valid_receipt,
        commands=[
            CommandEvidence(
                argv=["uv", "run", "pytest"],
                exit_code=0,
                output_path="pytest.txt",
                output_sha256=hashlib.sha256(output_bytes).hexdigest(),
            )
        ],
        at=NOW,
    )
    assert admitted.cars["A6-G0"].state is CarState.IMPLEMENTATION_ADMITTED


def test_integration_records_facts_without_granting_checker_authority() -> None:
    admitted = admitted_ledger()
    receipt = EvidenceReceipt(
        path="evidence/integration.json",
        sha256=SHA,
        author_id="integrator",
        verdict="RECORDED",
        observed_revision="b" * 64,
    )

    integrated = PortfolioLedgerService(admitted).integrate(
        "A6-G0",
        integrator_id="integrator",
        integration_sha="b" * 64,
        expected_implementation_sha=SHA,
        receipt=receipt,
        at=NOW,
    )

    assert integrated.cars["A6-G0"].state is CarState.INTEGRATED
    assert integrated.cars["A6-G0"].integrator_id == "integrator"
    with pytest.raises(LedgerRefusal, match="integrator authority"):
        PortfolioLedgerService(admitted).integrate(
            "A6-G0",
            integrator_id="checker",
            integration_sha="b" * 64,
            expected_implementation_sha=SHA,
            receipt=receipt.model_copy(update={"author_id": "checker"}),
            at=NOW,
        )


def test_only_aspect_aggregates_can_be_certified_by_a_distinct_checker() -> None:
    aggregate = integrated_ledger(car_kind=CarKind.ASPECT_AGGREGATE)
    receipt = EvidenceReceipt(
        path="evidence/aspect.json", sha256=SHA, author_id="checker-2", verdict="PASS", observed_revision="b" * 64
    )

    certified = PortfolioLedgerService(aggregate).certify_aspect(
        "A6-G0", checker_id="checker-2", report=receipt.path, receipt=receipt, at=NOW
    )

    assert certified.cars["A6-G0"].state is CarState.ASPECT_CERTIFIED
    implementation = integrated_ledger()
    with pytest.raises(LedgerRefusal, match="aspect aggregate"):
        PortfolioLedgerService(implementation).certify_aspect(
            "A6-G0", checker_id="checker-2", report=receipt.path, receipt=receipt, at=NOW
        )


def test_aspect_certification_requires_every_consumer_integration_sha_as_predecessor() -> None:
    aggregate = integrated_ledger(car_kind=CarKind.ASPECT_AGGREGATE)
    consumer = aggregate.cars["A6-G0"].model_copy(
        update={"id": "A6-CONSUMER", "issue": 9997, "car_kind": CarKind.IMPLEMENTATION}
    )
    aggregate_car = aggregate.cars["A6-G0"].model_copy(update={"predecessor_shas": []})
    aggregate = aggregate.model_copy(update={"cars": {aggregate_car.id: aggregate_car, consumer.id: consumer}})
    receipt = EvidenceReceipt(
        path="evidence/aspect.json", sha256=SHA, author_id="checker-2", verdict="PASS", observed_revision="b" * 64
    )
    with pytest.raises(LedgerRefusal, match="consumer integration revisions"):
        PortfolioLedgerService(aggregate).certify_aspect(
            "A6-G0", checker_id="checker-2", report=receipt.path, receipt=receipt, at=NOW
        )


def test_parent_certification_requires_all_aggregates_addenda_and_parent_checker() -> None:
    aggregate = integrated_ledger(car_kind=CarKind.ASPECT_AGGREGATE)
    aspect_receipt = EvidenceReceipt(
        path="evidence/aspect.json", sha256=SHA, author_id="checker-2", verdict="PASS", observed_revision="b" * 64
    )
    certified = PortfolioLedgerService(aggregate).certify_aspect(
        "A6-G0", checker_id="checker-2", report=aspect_receipt.path, receipt=aspect_receipt, at=NOW
    )
    required_car = certified.cars["A6-G0"].model_copy(update={"required_for_parent": True})
    certified = certified.model_copy(
        update={
            "cars": {"A6-G0": required_car},
            "parent": Parent(
                state=ParentState.INVENTORIED, required_car_ids=["A6-G0"], required_addendum_ids=["A6-final"]
            ),
        }
    )
    addendum_receipt = EvidenceReceipt(
        path="evidence/addendum.json", sha256=SHA, author_id="checker-3", verdict="PASS", observed_revision="b" * 64
    )
    with_addendum = PortfolioLedgerService(certified).record_addendum(
        Addendum(
            id="A6-final",
            car_id="A6-G0",
            revision="b" * 64,
            checker_id="checker-3",
            report=addendum_receipt.path,
            receipt=addendum_receipt,
        )
    )
    parent_receipt = EvidenceReceipt(
        path="evidence/parent.json", sha256=SHA, author_id="parent-checker", verdict="PASS", observed_revision="b" * 64
    )

    parent_certified = PortfolioLedgerService(with_addendum).certify_parent(
        checker_id="parent-checker", revision="b" * 64, report=parent_receipt.path, receipt=parent_receipt
    )

    assert parent_certified.parent.state is ParentState.PARENT_CERTIFIED
    persisted = parent_certified.model_dump(mode="json")
    persisted["parent"]["addenda"][0]["receipt"]["verdict"] = "REFUSED"
    with pytest.raises(ValueError, match=r"certified parent addendum|addendum 'A6-final' is invalid"):
        PortfolioLedger.model_validate(persisted)
    with pytest.raises(LedgerRefusal, match="parent-checker authority"):
        PortfolioLedgerService(with_addendum).certify_parent(
            checker_id="checker",
            revision="b" * 64,
            report=parent_receipt.path,
            receipt=parent_receipt.model_copy(update={"author_id": "checker"}),
        )
    with pytest.raises(LedgerRefusal, match="does not incorporate"):
        PortfolioLedgerService(with_addendum).certify_parent(
            checker_id="parent-checker",
            revision="c" * 64,
            report=parent_receipt.path,
            receipt=parent_receipt.model_copy(update={"observed_revision": "c" * 64}),
        )


def test_parent_certification_cannot_omit_a_car_marked_required() -> None:
    aggregate = integrated_ledger(car_kind=CarKind.ASPECT_AGGREGATE)
    aspect_receipt = EvidenceReceipt(
        path="evidence/aspect.json", sha256=SHA, author_id="checker-2", verdict="PASS", observed_revision="b" * 64
    )
    certified = PortfolioLedgerService(aggregate).certify_aspect(
        "A6-G0", checker_id="checker-2", report=aspect_receipt.path, receipt=aspect_receipt, at=NOW
    )
    first = certified.cars["A6-G0"].model_copy(update={"required_for_parent": True})
    omitted = first.model_copy(update={"id": "A6-OMITTED", "issue": 9998})
    certified = certified.model_copy(
        update={
            "cars": {first.id: first, omitted.id: omitted},
            "parent": Parent(state=ParentState.INVENTORIED, required_car_ids=[first.id]),
        }
    )
    receipt = EvidenceReceipt(
        path="evidence/parent.json", sha256=SHA, author_id="parent-checker", verdict="PASS", observed_revision="b" * 64
    )

    with pytest.raises(LedgerRefusal, match="required car set"):
        PortfolioLedgerService(certified).certify_parent(
            checker_id="parent-checker", revision="b" * 64, report=receipt.path, receipt=receipt
        )


def test_atomic_store_round_trip_and_failed_replace_preserves_previous_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    store = LedgerStore(ledger_path, lock_path)
    written = store.write(minimum_ledger())

    assert store.read() == written
    assert written.ledger_sha256 is not None
    assert lock_path.exists()
    assert list(tmp_path.glob("*.tmp")) == []

    def fail_replace(source: str | Path, target: str | Path) -> None:
        raise OSError("simulated crash before rename")

    monkeypatch.setattr("dh_core.portfolio_ledger.os.replace", fail_replace)
    changed = written.model_copy(update={"portfolio_issue": 9999})
    with pytest.raises(OSError, match="simulated crash"):
        store.write_transition(changed, expected_ledger_sha256=written.ledger_sha256)

    assert store.read() == written
    assert list(tmp_path.glob("*.tmp")) == []


def test_initialization_is_create_only_and_preserves_existing_history(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path / "ledger.json", tmp_path / "ledger.lock")
    existing = minimum_ledger()
    car = existing.cars["A6-G0"].model_copy(
        update={
            "history": [
                HistoryEvent(
                    action="inventory",
                    actor_id="maker",
                    at=NOW,
                    from_state="INVENTORIED",
                    to_state="INVENTORIED",
                    inventory_ids=["inventory-a6-g0"],
                    reservation_id=None,
                    receipt_sha256=SHA,
                )
            ]
        }
    )
    first = store.initialize(existing.model_copy(update={"cars": {car.id: car}}))

    with pytest.raises(LedgerRefusal, match="already exists"):
        store.initialize(minimum_ledger().model_copy(update={"portfolio_issue": 9999}))

    assert store.read() == first
    assert store.read().cars["A6-G0"].history == car.history


def test_initialization_refuses_missing_tracker_correction_and_inventory_bytes(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path / "ledger.json", tmp_path / "ledger.lock", evidence_root=tmp_path)

    with pytest.raises(LedgerRefusal, match=r"tracker manifest.*does not exist"):
        store.initialize(minimum_ledger())

    assert not (tmp_path / "ledger.json").exists()


def test_inventory_validation_uses_frozen_git_revision_after_worktree_edit(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=10)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Ledger Test"], check=True, timeout=10)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "ledger@example.invalid"], check=True, timeout=10
    )
    source = tmp_path / "product.py"
    baseline = b"value = 'baseline'\n"
    source.write_bytes(baseline)
    subprocess.run(["git", "-C", str(tmp_path), "add", "product.py"], check=True, timeout=10)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "baseline"], check=True, timeout=10)
    revision = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()
    blob = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", f"{revision}:product.py"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    path = InventoryPath(path="product.py", git_blob=blob, sha256=hashlib.sha256(baseline).hexdigest())
    inventory = Inventory(id="inventory-a6-g0", revision=revision, paths=[path], sha256=inventory_sha256([path]))
    ledger = minimum_ledger()
    car = ledger.cars["A6-G0"].model_copy(update={"base_git_sha": revision, "upstream_git_sha": revision})
    groups = dict(ledger.conflict_groups)
    groups["CG-PORTFOLIO-LEDGER"] = ConflictGroup(id="CG-PORTFOLIO-LEDGER", paths=["product.py"])
    ledger = ledger.model_copy(
        update={"cars": {car.id: car}, "inventories": {inventory.id: inventory}, "conflict_groups": groups}
    )
    reservation_receipt = b'{"reservation":"product.py"}'
    (tmp_path / "reservation.json").write_bytes(reservation_receipt)
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["product.py"],
        owner="maker",
        owner_process_id=os.getpid(),
        state=ReservationState.ACTIVE,
        lock_path="ledger.lock",
        acquired_at=NOW,
        receipt_path="reservation.json",
        receipt_sha256=hashlib.sha256(reservation_receipt).hexdigest(),
    )
    reserved = PortfolioLedgerService(ledger, evidence_root=tmp_path).acquire_reservation(
        "A6-G0", reservation, actor_id="maker"
    )
    source.write_text("value = 'candidate edit'\n", encoding="utf-8")

    LedgerStore(
        tmp_path / "ledger.json", tmp_path / "ledger.lock", evidence_root=tmp_path
    ).validate_inventory_and_reservation_evidence(reserved, PortfolioLedgerService(reserved, evidence_root=tmp_path))
    release_receipt = b'{"release":"after candidate edit"}'
    (tmp_path / "release.json").write_bytes(release_receipt)
    released = PortfolioLedgerService(reserved, evidence_root=tmp_path).release_reservation(
        "A6-G0",
        reservation.id,
        actor_id="maker",
        at=NOW,
        receipt_path="release.json",
        receipt_sha256=hashlib.sha256(release_receipt).hexdigest(),
    )
    assert released.reservations[reservation.id].state is ReservationState.RELEASED


def test_archived_inventory_verification_does_not_require_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archived = b"immutable archived baseline\n"
    (tmp_path / "archived.py").write_bytes(archived)
    path = InventoryPath(path="archived.py", git_blob=SHA, sha256=hashlib.sha256(archived).hexdigest())
    inventory = Inventory(id="inventory-a6-g0", revision=SHA, paths=[path], sha256=inventory_sha256([path]))
    ledger = minimum_ledger().model_copy(update={"inventories": {inventory.id: inventory}})
    store = LedgerStore(tmp_path / "ledger.json", tmp_path / "ledger.lock", evidence_root=tmp_path)
    monkeypatch.setattr("dh_core.portfolio_ledger.shutil.which", lambda _name: None)

    store.verify_inventory_path(inventory, path, PortfolioLedgerService(ledger, evidence_root=tmp_path))


def test_inventory_git_timeout_becomes_structured_refusal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = inventory_record().paths[0]
    inventory = inventory_record()
    ledger = minimum_ledger()
    store = LedgerStore(tmp_path / "ledger.json", tmp_path / "ledger.lock", evidence_root=tmp_path)
    monkeypatch.setattr("dh_core.portfolio_ledger.shutil.which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(
        "dh_core.portfolio_ledger.subprocess.run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("git", 30)),
    )
    with pytest.raises(LedgerRefusal, match="timed out"):
        store.verify_inventory_path(inventory, path, PortfolioLedgerService(ledger, evidence_root=tmp_path))


def test_remote_mirror_read_has_explicit_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed: dict[str, float] = {}

    def stalled(_url: str, *, timeout: float) -> None:
        observed["timeout"] = timeout
        raise OSError("stalled mirror")

    class Opener:
        open = staticmethod(stalled)

    monkeypatch.setattr("dh_core.portfolio_ledger.urllib.request.build_opener", lambda *_args: Opener())
    with pytest.raises(LedgerRefusal, match="cannot read mirror"):
        LedgerStore(tmp_path / "ledger.json", tmp_path / "ledger.lock").read_url("https://example.invalid/mirror")
    assert observed["timeout"] == pytest.approx(30, abs=0.01)


def test_total_mirror_deadline_includes_open_and_all_reads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class Response:
        fp = None

        def __init__(self, chunks: list[bytes]) -> None:
            self.chunks = iter(chunks)

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int) -> bytes:
            return next(self.chunks)

    observed: list[float] = []

    class Opener:
        @staticmethod
        def open(_url: str, *, timeout: float) -> Response:
            observed.append(timeout)
            return Response([b"x", b""])

    monkeypatch.setattr("dh_core.portfolio_ledger.urllib.request.build_opener", lambda *_args: Opener())
    clock = iter([0.0, 0.0, 29.0, 33.0])
    monkeypatch.setattr("dh_core.portfolio_ledger.time.monotonic", lambda: next(clock))
    store = LedgerStore(tmp_path / "ledger.json", tmp_path / "ledger.lock")
    with pytest.raises(LedgerRefusal, match="total deadline"):
        store.read_url("https://example.invalid/mirror")
    assert observed == [30.0]

    clock = iter([0.0, 0.0, 10.0, 20.0])
    monkeypatch.setattr("dh_core.portfolio_ledger.time.monotonic", lambda: next(clock))
    assert store.read_url("https://example.invalid/mirror") == b"x"


def test_compare_and_swap_rejects_a_transition_from_a_stale_process_read(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path / "ledger.json", tmp_path / "ledger.lock")
    source = store.write(minimum_ledger())
    first_reservation = Reservation(
        id="first",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path=str(tmp_path / "ledger.lock"),
        acquired_at=NOW,
        receipt_path="evidence/reservation.json",
        receipt_sha256=SHA,
    )
    first = PortfolioLedgerService(source).acquire_reservation("A6-G0", first_reservation, actor_id="maker")
    second = PortfolioLedgerService(source).acquire_reservation(
        "A6-G0", first_reservation.model_copy(update={"id": "second"}), actor_id="maker"
    )

    store.write_transition(first, expected_ledger_sha256=source.ledger_sha256)
    with pytest.raises(LedgerRefusal, match="stale ledger revision"):
        store.write_transition(second, expected_ledger_sha256=source.ledger_sha256)

    assert store.read().reservations.keys() == {"first"}


def test_mirror_comparison_and_missing_local_restoration_are_fail_closed(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    mirror_path = tmp_path / "mirror.json"
    store = LedgerStore(ledger_path, lock_path)
    ledger = minimum_ledger().model_copy(update={"mirror": Mirror(url=mirror_path.as_uri(), expected_sha256="0" * 64)})
    written = store.write(ledger)
    mirror_path.write_bytes(ledger_path.read_bytes())

    assert store.verify_mirror() == written
    ledger_path.unlink()
    assert store.restore_from_mirror(mirror_url=mirror_path.as_uri(), expected_sha256=written.ledger_sha256) == written
    assert ledger_path.read_bytes() == mirror_path.read_bytes()

    ledger_path.unlink()
    with pytest.raises(LedgerRefusal, match="externally recorded digest"):
        store.restore_from_mirror(mirror_url=mirror_path.as_uri(), expected_sha256="b" * 64)
    store.restore_from_mirror(mirror_url=mirror_path.as_uri(), expected_sha256=written.ledger_sha256)

    mirror_path.write_text("{}", encoding="utf-8")
    with pytest.raises(LedgerRefusal, match="mirror"):
        store.verify_mirror()


def test_mirrored_transition_publishes_exact_new_bytes_before_local_commit(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    first_mirror = tmp_path / "mirror-v1.json"
    second_mirror = tmp_path / "mirror-v2.json"
    store = LedgerStore(ledger_path, lock_path)
    current = store.write(
        minimum_ledger().model_copy(update={"mirror": Mirror(url=first_mirror.as_uri(), expected_sha256="0" * 64)})
    )
    first_mirror.write_bytes(ledger_path.read_bytes())
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path=str(lock_path),
        acquired_at=NOW,
        receipt_path="evidence/reservation.json",
        receipt_sha256=SHA,
    )
    transitioned = PortfolioLedgerService(current).acquire_reservation("A6-G0", reservation, actor_id="maker")
    transitioned = transitioned.model_copy(
        update={"mirror": Mirror(url=second_mirror.as_uri(), expected_sha256="0" * 64)}
    )

    written = store.write_transition(transitioned, expected_ledger_sha256=current.ledger_sha256)

    assert second_mirror.read_bytes() == ledger_path.read_bytes()
    assert store.verify_mirror() == written


def test_mirror_publication_failure_keeps_previous_local_revision_readable(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    first_mirror = tmp_path / "mirror-v1.json"
    occupied_mirror = tmp_path / "occupied-v2.json"
    store = LedgerStore(ledger_path, lock_path)
    current = store.write(
        minimum_ledger().model_copy(update={"mirror": Mirror(url=first_mirror.as_uri(), expected_sha256="0" * 64)})
    )
    first_mirror.write_bytes(ledger_path.read_bytes())
    occupied_mirror.write_text("immutable unrelated bytes", encoding="utf-8")
    candidate = current.model_copy(
        update={
            "portfolio_issue": 9999,
            "mirror": Mirror(url=occupied_mirror.as_uri(), expected_sha256="0" * 64),
            "ledger_sha256": None,
        }
    )

    with pytest.raises(LedgerRefusal, match="mirror publication"):
        store.write_transition(candidate, expected_ledger_sha256=current.ledger_sha256)

    assert ledger_path.read_bytes() == first_mirror.read_bytes()
    assert store.verify_mirror() == current


def test_restore_refuses_a_local_revision_created_during_mirror_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    mirror_path = tmp_path / "mirror.json"
    store = LedgerStore(ledger_path, lock_path)
    mirrored = store.write(
        minimum_ledger().model_copy(update={"mirror": Mirror(url=mirror_path.as_uri(), expected_sha256="0" * 64)})
    )
    mirror_bytes = ledger_path.read_bytes()
    mirror_path.write_bytes(mirror_bytes)
    competing_path = tmp_path / "competing.json"
    competing = LedgerStore(competing_path, tmp_path / "competing.lock").write(
        minimum_ledger().model_copy(update={"portfolio_issue": 9999})
    )
    ledger_path.unlink()

    def racing_read(_url: str) -> bytes:
        ledger_path.write_bytes(competing.canonical_bytes())
        return mirror_bytes

    monkeypatch.setattr(store, "read_url", racing_read)
    with pytest.raises(LedgerRefusal, match="appeared during mirror restoration"):
        store.restore_from_mirror(mirror_url=mirror_path.as_uri(), expected_sha256=mirrored.ledger_sha256)

    assert PortfolioLedger.model_validate_json(ledger_path.read_bytes()).portfolio_issue == 9999


def test_directory_durability_uses_posix_fsync_and_skips_unsupported_windows_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = LedgerStore(tmp_path / "ledger.json", tmp_path / "ledger.lock")
    calls: list[tuple[str, int | Path]] = []

    monkeypatch.setattr("dh_core.portfolio_ledger.os.name", "nt")
    monkeypatch.setattr("dh_core.portfolio_ledger.os.open", lambda path, flags: calls.append(("open", path)) or 41)
    store.sync_directory(tmp_path)
    assert calls == []

    monkeypatch.setattr("dh_core.portfolio_ledger.os.name", "posix")
    monkeypatch.setattr("dh_core.portfolio_ledger.os.fsync", lambda fd: calls.append(("fsync", fd)))
    monkeypatch.setattr("dh_core.portfolio_ledger.os.close", lambda fd: calls.append(("close", fd)))
    store.sync_directory(tmp_path)
    assert calls == [("open", tmp_path), ("fsync", 41), ("close", 41)]


def test_windows_file_uri_round_trips_drive_and_unc_paths_without_posix_coercion() -> None:
    drive_path = PureWindowsPath(r"C:\tmp\mirror.json")
    drive_uri = file_path_to_uri(str(drive_path), platform="nt")
    decoded_drive = PureWindowsPath(file_uri_to_path(drive_uri, platform="nt"))
    assert drive_uri == "file:///C:/tmp/mirror.json"
    assert decoded_drive == drive_path
    assert decoded_drive.drive == "C:"
    assert decoded_drive.is_absolute()

    unc_path = PureWindowsPath(r"\\server\share\evidence\mirror.json")
    unc_uri = file_path_to_uri(str(unc_path), platform="nt")
    decoded_unc = PureWindowsPath(file_uri_to_path(unc_uri, platform="nt"))
    assert unc_uri == "file://server/share/evidence/mirror.json"
    assert decoded_unc == unc_path
    assert decoded_unc.drive == r"\\server\share"
    assert decoded_unc.is_absolute()


def test_agent_cli_show_emits_one_compact_complete_json_object(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    written = LedgerStore(ledger_path, lock_path).write(materialized_ledger(tmp_path))
    script = Path(__file__).parents[1] / "scripts" / "portfolio_ledger.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--ledger",
            str(ledger_path),
            "--lock",
            str(lock_path),
            "--evidence-root",
            str(tmp_path),
            "show",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "\n" not in result.stdout.rstrip("\n")
    assert json.loads(result.stdout) == written.model_dump(mode="json")


def test_concurrent_and_retried_cli_initialization_admits_exactly_one_creator(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    request_path = tmp_path / "initialize.json"
    request_path.write_text(materialized_ledger(tmp_path).model_dump_json(), encoding="utf-8")
    script = Path(__file__).parents[1] / "scripts" / "portfolio_ledger.py"
    command = [
        sys.executable,
        str(script),
        "--ledger",
        str(ledger_path),
        "--lock",
        str(lock_path),
        "--evidence-root",
        str(tmp_path),
        "initialize",
        "--request",
        str(request_path),
    ]
    processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(4)]
    results = [(*process.communicate(timeout=10), process.returncode) for process in processes]

    assert sum(return_code == 0 for _stdout, _stderr, return_code in results) == 1
    retry = subprocess.run(command, check=False, capture_output=True, text=True, timeout=10)
    assert retry.returncode == 1
    assert "already exists" in retry.stderr
    assert LedgerStore(ledger_path, lock_path, evidence_root=tmp_path).read().portfolio_issue == 3620


def test_agent_cli_executes_reservation_transition_from_complete_json_request(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    request_path = tmp_path / "request.json"
    LedgerStore(ledger_path, lock_path).write(materialized_ledger(tmp_path))
    receipt_bytes = b'{"reservation":"A6-G0"}'
    (tmp_path / "reservation.json").write_bytes(receipt_bytes)
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        owner_process_id=os.getpid(),
        state=ReservationState.ACTIVE,
        lock_path=str(lock_path),
        acquired_at=NOW,
        receipt_path="reservation.json",
        receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
    )
    request_path.write_text(
        json.dumps({"car_id": "A6-G0", "actor_id": "maker", "reservation": reservation.model_dump(mode="json")}),
        encoding="utf-8",
    )
    script = Path(__file__).parents[1] / "scripts" / "portfolio_ledger.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--ledger",
            str(ledger_path),
            "--lock",
            str(lock_path),
            "--evidence-root",
            str(tmp_path),
            "reservation-acquire",
            "--request",
            str(request_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["cars"]["A6-G0"]["state"] == "RESERVED"
    assert LedgerStore(ledger_path, lock_path).read().cars["A6-G0"].state is CarState.RESERVED


def test_agent_cli_immediately_rejects_untyped_extra_request_fields(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    request_path = tmp_path / "request.json"
    LedgerStore(ledger_path, lock_path).write(materialized_ledger(tmp_path))
    receipt = b'{"reservation":"typed-boundary"}'
    (tmp_path / "reservation.json").write_bytes(receipt)
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        owner_process_id=os.getpid(),
        state=ReservationState.ACTIVE,
        lock_path=str(lock_path),
        acquired_at=NOW,
        receipt_path="reservation.json",
        receipt_sha256=hashlib.sha256(receipt).hexdigest(),
    )
    request_path.write_text(
        json.dumps({
            "car_id": "A6-G0",
            "actor_id": "maker",
            "reservation": reservation.model_dump(mode="json"),
            "unexpected": "must not cross the boundary",
        }),
        encoding="utf-8",
    )
    script = Path(__file__).parents[1] / "scripts" / "portfolio_ledger.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--ledger",
            str(ledger_path),
            "--lock",
            str(lock_path),
            "--evidence-root",
            str(tmp_path),
            "reservation-acquire",
            "--request",
            str(request_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 1
    assert "extra_forbidden" in result.stderr
    assert LedgerStore(ledger_path, lock_path).read().cars["A6-G0"].state is CarState.INVENTORIED


def test_agent_cli_mirrored_transition_is_immediately_readable(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    first_mirror = tmp_path / "mirror-v1.json"
    second_mirror = tmp_path / "mirror-v2.json"
    request_path = tmp_path / "request.json"
    ledger = materialized_ledger(tmp_path).model_copy(
        update={"mirror": Mirror(url=first_mirror.as_uri(), expected_sha256="0" * 64)}
    )
    LedgerStore(ledger_path, lock_path).write(ledger)
    receipt_bytes = b'{"reservation":"A6-G0"}'
    (tmp_path / "reservation.json").write_bytes(receipt_bytes)
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        owner_process_id=os.getpid(),
        state=ReservationState.ACTIVE,
        lock_path=str(lock_path),
        acquired_at=NOW,
        receipt_path="reservation.json",
        receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
    )
    request_path.write_text(
        json.dumps({
            "car_id": "A6-G0",
            "actor_id": "maker",
            "reservation": reservation.model_dump(mode="json"),
            "mirror_url": second_mirror.as_uri(),
        }),
        encoding="utf-8",
    )
    script = Path(__file__).parents[1] / "scripts" / "portfolio_ledger.py"
    base_command = [
        sys.executable,
        str(script),
        "--ledger",
        str(ledger_path),
        "--lock",
        str(lock_path),
        "--evidence-root",
        str(tmp_path),
    ]

    transition_result = subprocess.run(
        [*base_command, "reservation-acquire", "--request", str(request_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    show_result = subprocess.run([*base_command, "show"], check=False, capture_output=True, text=True, timeout=10)

    assert transition_result.returncode == 0, transition_result.stderr
    assert show_result.returncode == 0, show_result.stderr
    assert second_mirror.read_bytes() == ledger_path.read_bytes()
    assert json.loads(show_result.stdout)["cars"]["A6-G0"]["state"] == "RESERVED"


def test_concurrent_cli_processes_admit_only_one_incompatible_reservation(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    LedgerStore(ledger_path, lock_path).write(materialized_ledger(tmp_path))
    script = Path(__file__).parents[1] / "scripts" / "portfolio_ledger.py"
    processes: list[subprocess.Popen[str]] = []
    for number in range(4):
        request_path = tmp_path / f"request-{number}.json"
        receipt_path = tmp_path / f"reservation-{number}.json"
        receipt_bytes = json.dumps({"reservation": number}, separators=(",", ":")).encode()
        receipt_path.write_bytes(receipt_bytes)
        reservation = Reservation(
            id=f"reservation-{number}",
            group="CG-PORTFOLIO-LEDGER",
            paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
            owner="maker",
            owner_process_id=os.getpid(),
            state=ReservationState.ACTIVE,
            lock_path=str(lock_path),
            acquired_at=NOW,
            receipt_path=receipt_path.name,
            receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
        )
        request_path.write_text(
            json.dumps({"car_id": "A6-G0", "actor_id": "maker", "reservation": reservation.model_dump(mode="json")}),
            encoding="utf-8",
        )
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    str(script),
                    "--ledger",
                    str(ledger_path),
                    "--lock",
                    str(lock_path),
                    "--evidence-root",
                    str(tmp_path),
                    "reservation-acquire",
                    "--request",
                    str(request_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )

    results = [(*process.communicate(timeout=10), process.returncode) for process in processes]

    assert sum(return_code == 0 for _stdout, _stderr, return_code in results) == 1
    final = LedgerStore(ledger_path, lock_path).read()
    assert len([item for item in final.reservations.values() if item.state is ReservationState.ACTIVE]) == 1


def test_agent_cli_exposes_the_complete_transition_and_recovery_interface() -> None:
    script = Path(__file__).parents[1] / "scripts" / "portfolio_ledger.py"

    result = subprocess.run(
        [sys.executable, str(script), "--help"], check=False, capture_output=True, text=True, timeout=10
    )

    assert result.returncode == 0
    for command in (
        "initialize",
        "inventory",
        "reservation-acquire",
        "reservation-release",
        "reservation-invalidate",
        "reservation-recover",
        "implementation-admit",
        "integrate",
        "aspect-certify",
        "addendum-record",
        "parent-certify",
        "verify-mirror",
        "restore",
        "show",
    ):
        assert command in result.stdout


def test_checker_hostile_authority_reconstruction_and_mirror_outcomes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(LedgerRefusal) as missing_root:
        PortfolioLedgerRuntime(evidence_root=None)
    assert (missing_root.value.category, missing_root.value.code) == ("unavailable", "missing_evidence")

    payload = minimum_ledger().model_dump(mode="json")
    payload["correction_rows"]["R01"]["owner"] = "undeclared"
    with pytest.raises(ValueError, match="undeclared"):
        PortfolioLedger.model_validate(payload)

    with pytest.raises(ValueError, match="present together"):
        Mirror(expected_sha256=SHA)
    with pytest.raises(LedgerRefusal, match="drive cannot appear in authority"):
        file_uri_to_path("file://C:/path/mirror.json", platform="nt")

    store = LedgerStore(tmp_path / "ledger.json", tmp_path / "ledger.lock")
    called: list[str] = []
    monkeypatch.setattr(store, "read_url", lambda url: called.append(url) or b"")
    with pytest.raises(LedgerRefusal, match="unsupported scheme"):
        store.restore_from_mirror(mirror_url="ftp://user@example.invalid:21/mirror?x=1", expected_sha256=SHA)
    assert called == []
