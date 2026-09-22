"""T2 reconstruction-root and stored-query tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from dh_core.ledger import store
from dh_core.merge_train import ExplainQuery, MergeNext, MergeQuery

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
