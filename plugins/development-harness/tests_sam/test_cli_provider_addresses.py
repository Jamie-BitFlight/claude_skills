from __future__ import annotations

import json

import pytest
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import ContentKind, ContentQuery, ContentRef, ContentWrite
from sam_schema import sam_plan
from sam_schema.cli import app
from sam_schema.core.backends.content import ContentTaskProvider
from typer.testing import CliRunner

runner = CliRunner()


def _put_plan(provider: InMemoryBackend, plan_id: str, feature: str, *, owner_reference: str = "") -> None:
    provider.put_content(
        ContentWrite(
            reference=ContentRef(kind=ContentKind.PLAN, name=plan_id),
            content=json.dumps(
                {
                    "plan_id": plan_id,
                    "feature": feature,
                    "version": "1.0.0",
                    "description": "",
                    "goal": "Exercise provider addressing",
                    "context": "",
                    "acceptance_criteria": "",
                    "issue": None,
                    "tasks": [],
                    "source_path": None,
                    "state": "drafting",
                },
                separators=(",", ":"),
            ),
            owner_reference=owner_reference,
        )
    )


@pytest.mark.parametrize(
    ("address", "expected_plan_id"), [("P1", "P1"), ("Pa1b2c3d4", "Pa1b2c3d4"), ("provider-slug", "P2")]
)
def test_read_resolves_provider_plan_addresses(
    monkeypatch: pytest.MonkeyPatch, address: str, expected_plan_id: str
) -> None:
    # Given: provider-native plans with legacy, UUID, and slug identities.
    provider = InMemoryBackend()
    _put_plan(provider, "P1", "legacy")
    _put_plan(provider, "Pa1b2c3d4", "uuid")
    _put_plan(provider, "P2", "provider-slug")
    monkeypatch.setattr(sam_plan, "_backend", lambda: ContentTaskProvider(provider))

    # When: an agent reads the plan through the grouped CLI.
    result = runner.invoke(app, ["plan", "read", "--address", address])

    # Then: the CLI returns the plan selected by its logical provider identity.
    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout)["plan"]["plan-id"] == expected_plan_id


def test_create_persists_opaque_owner_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: an empty provider-backed SAM CLI.
    provider = InMemoryBackend()
    monkeypatch.setattr(sam_plan, "_backend", lambda: ContentTaskProvider(provider))

    # When: an agent creates a plan owned by an opaque work-item reference.
    result = runner.invoke(
        app, ["plan", "create", "--slug", "owned-plan", "--goal", "Persist ownership", "--owner-reference", "bd-a1b2"]
    )

    # Then: the provider persists the plan under that owner.
    assert result.exit_code == 0, result.stderr
    plan_id = json.loads(result.stdout)["plan_id"]
    records = provider.list_content(ContentQuery(kind=ContentKind.PLAN, owner_reference="bd-a1b2"))
    assert [record.reference.name for record in records] == [plan_id]


def test_update_reassigns_opaque_owner_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: a provider-backed plan with an existing owner.
    provider = InMemoryBackend()
    _put_plan(provider, "P1", "owned-plan", owner_reference="bd-old")
    monkeypatch.setattr(sam_plan, "_backend", lambda: ContentTaskProvider(provider))

    # When: an agent assigns a new opaque owner without an unrelated field update.
    result = runner.invoke(app, ["plan", "update", "--plan-address", "P1", "--owner-reference", "bd-new"])

    # Then: the owner assignment is persisted.
    assert result.exit_code == 0, result.stderr
    record = provider.get_content(ContentRef(kind=ContentKind.PLAN, name="P1"))
    assert record.owner_reference == "bd-new"
