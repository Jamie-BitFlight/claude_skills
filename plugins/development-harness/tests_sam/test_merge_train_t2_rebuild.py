"""T2 reconstruction-root and stored-query tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from dh_core.ledger import store
from dh_core.merge_train import ExplainQuery, MergeNext, MergeQuery, SubmitCandidate

from tests_sam.run_merge_train_t2_mutations import MUTANTS, PLUGIN
from tests_sam.test_merge_train_t2_candidates import accept_assignment, service
from tests_sam.test_merge_train_t2_claims import admitted


def test_f18_t2_rebuild_matches_candidate_and_claim_projection(tmp_path: Path) -> None:
    train, connection, integrator, _policies, _gates, _branch = admitted(tmp_path)
    train.merge_next(MergeNext(plan="Pt2", generation=1, integrator=integrator))
    before_candidates = store.rows_of(connection.execute("SELECT * FROM merge_candidates ORDER BY candidate_number"))
    before_claims = store.rows_of(connection.execute("SELECT * FROM merge_claims ORDER BY claim_number"))

    store.rebuild(connection)

    assert (
        store.rows_of(connection.execute("SELECT * FROM merge_candidates ORDER BY candidate_number"))
        == before_candidates
    )
    assert store.rows_of(connection.execute("SELECT * FROM merge_claims ORDER BY claim_number")) == before_claims
    assert train.validate(MergeQuery(plan="Pt2")).valid
    assert train.explain(ExplainQuery(plan="Pt2")).blockers == ["no-admitted-candidate"]


def test_f18_missing_evidence_rolls_back_before_projection_delete(tmp_path: Path) -> None:
    _train, connection, _integrator, _policies, _gates, _branch = admitted(tmp_path)
    before = store.rows_of(connection.execute("SELECT * FROM merge_candidates"))
    connection.execute("DELETE FROM merge_evidence_blobs")

    with pytest.raises(LookupError, match="unresolved evidence"):
        store.rebuild(connection)

    assert store.rows_of(connection.execute("SELECT * FROM merge_candidates")) == before


def test_f10_rebuild_rejects_invalid_typed_json_evidence(tmp_path: Path) -> None:
    train, connection = service(tmp_path)
    maker = accept_assignment(train, connection, "T1")
    invalid = train.evidence.put(b"not-json", "application/json")
    train.submit(
        SubmitCandidate(
            plan="Pt2",
            generation=1,
            branch="candidate",
            pull_request_ref="PR1",
            candidate_sha="b" * 40,
            base_sha="a" * 40,
            maker=maker,
            maker_evidence_digest=invalid.digest,
        )
    )

    with pytest.raises(ValueError, match="Expecting value"):
        store.rebuild(connection)


def test_f25_t2_mutation_manifest_is_complete_and_each_seam_unique() -> None:
    assert [mutant.identity for mutant in MUTANTS] == [f"T2-M{index:02d}" for index in range(1, 29)]
    for mutant in MUTANTS:
        assert (PLUGIN / mutant.file).read_text(encoding="utf-8").count(mutant.old) == 1, mutant.identity
        assert "::test_" in mutant.selector
