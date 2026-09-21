"""Contract tests for the canonical portfolio merge ledger."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from dh_core.portfolio_ledger import (
    Addendum,
    Car,
    CarKind,
    CarState,
    CommandEvidence,
    ConflictGroup,
    CorrectionRow,
    EvidenceReceipt,
    Inventory,
    InventoryPath,
    LedgerRefusal,
    LedgerStore,
    Mirror,
    Parent,
    ParentState,
    PortfolioLedger,
    PortfolioLedgerService,
    RecoveryEvidence,
    Reservation,
    ReservationState,
    Role,
    TrackerManifest,
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


def minimum_ledger() -> PortfolioLedger:
    """Build the smallest portfolio that satisfies the persisted schema."""
    return PortfolioLedger(
        portfolio_issue=3620,
        tracker_manifest=TrackerManifest(
            path=".tmp/reports/runtime-integrity-tracker-manifest.md", sha256=SHA, observed_at=NOW
        ),
        correction_rows={
            f"R{number:02d}": CorrectionRow(
                owner=f"owner-{number}", artifact=f"receipt-{number}.json", sha256=SHA, reviewer=f"reviewer-{number}"
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
        conflict_groups={
            "CG-PORTFOLIO-LEDGER": ConflictGroup(
                id="CG-PORTFOLIO-LEDGER", paths=["plugins/development-harness/dh_core/portfolio_ledger.py"]
            )
        },
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
            )
        },
        inventories={"inventory-a6-g0": inventory_record()},
        parent=Parent(state=ParentState.INVENTORIED, required_car_ids=[]),
        mirror=Mirror(),
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
        state=ReservationState.ACTIVE,
        lock_path="ledger.lock",
        acquired_at=NOW,
        receipt_sha256=SHA,
    )

    with pytest.raises(LedgerRefusal, match="inventory does not cover"):
        PortfolioLedgerService(ledger).acquire_reservation("A6-G0", reservation, actor_id="maker")


def test_reservation_release_invalidate_and_stale_recovery_return_to_inventory() -> None:
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path=".tmp/reports/runtime-integrity-merge-train-ledger.lock",
        acquired_at=NOW,
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

    third = reservation.model_copy(update={"id": "reservation-third"})
    stale = PortfolioLedgerService(invalidated).acquire_reservation("A6-G0", third, actor_id="maker")
    recovered = PortfolioLedgerService(stale).recover_reservation(
        "A6-G0",
        third.id,
        RecoveryEvidence(
            stale_owner_id="maker",
            process_id=1234,
            liveness_output_path="evidence/liveness.txt",
            liveness_output_sha256=SHA,
            prior_receipt_sha256=SHA,
            checker_id="checker",
            judgement_path="evidence/recovery.json",
            judgement_sha256=SHA,
            observed_at=NOW,
        ),
    )
    assert recovered.reservations[third.id].state is ReservationState.INVALIDATED
    assert recovered.cars["A6-G0"].state is CarState.INVENTORIED


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
    with pytest.raises(LedgerRefusal, match="parent-checker authority"):
        PortfolioLedgerService(with_addendum).certify_parent(
            checker_id="checker",
            revision="b" * 64,
            report=parent_receipt.path,
            receipt=parent_receipt.model_copy(update={"author_id": "checker"}),
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
        store.write(changed)

    assert store.read() == written
    assert list(tmp_path.glob("*.tmp")) == []


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
    ledger = minimum_ledger().model_copy(update={"mirror": Mirror(url=mirror_path.as_uri())})
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


def test_restore_refuses_a_local_revision_created_during_mirror_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    mirror_path = tmp_path / "mirror.json"
    store = LedgerStore(ledger_path, lock_path)
    mirrored = store.write(minimum_ledger().model_copy(update={"mirror": Mirror(url=mirror_path.as_uri())}))
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


def test_agent_cli_show_emits_one_compact_complete_json_object(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    written = LedgerStore(ledger_path, lock_path).write(minimum_ledger())
    script = Path(__file__).parents[1] / "scripts" / "portfolio_ledger.py"

    result = subprocess.run(
        [sys.executable, str(script), "--ledger", str(ledger_path), "--lock", str(lock_path), "show"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "\n" not in result.stdout.rstrip("\n")
    assert json.loads(result.stdout) == written.model_dump(mode="json")


def test_agent_cli_executes_reservation_transition_from_complete_json_request(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    request_path = tmp_path / "request.json"
    LedgerStore(ledger_path, lock_path).write(minimum_ledger())
    reservation = Reservation(
        id="reservation-a6-g0",
        group="CG-PORTFOLIO-LEDGER",
        paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
        owner="maker",
        state=ReservationState.ACTIVE,
        lock_path=str(lock_path),
        acquired_at=NOW,
        receipt_sha256=SHA,
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


def test_concurrent_cli_processes_admit_only_one_incompatible_reservation(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    lock_path = tmp_path / "ledger.lock"
    LedgerStore(ledger_path, lock_path).write(minimum_ledger())
    script = Path(__file__).parents[1] / "scripts" / "portfolio_ledger.py"
    processes: list[subprocess.Popen[str]] = []
    for number in range(4):
        request_path = tmp_path / f"request-{number}.json"
        reservation = Reservation(
            id=f"reservation-{number}",
            group="CG-PORTFOLIO-LEDGER",
            paths=["plugins/development-harness/dh_core/portfolio_ledger.py"],
            owner="maker",
            state=ReservationState.ACTIVE,
            lock_path=str(lock_path),
            acquired_at=NOW,
            receipt_sha256=SHA,
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
