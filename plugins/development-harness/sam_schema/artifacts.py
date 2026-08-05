"""Provider-neutral artifact command group."""

from __future__ import annotations

from typing import Annotated

import typer
from backlog_core.models import ArtifactStatus, ArtifactType
from dh_core import operations

from sam_schema.cli_output import emit_result, err

app = typer.Typer(help="Artifact manifest operations.", no_args_is_help=True, rich_markup_mode=None)


@app.command("register")
def register(
    item_id: Annotated[str, typer.Option("--item-id")],
    artifact_type: Annotated[ArtifactType, typer.Option("--artifact-type")],
    artifact_id: Annotated[str, typer.Option("--artifact-id")],
    status: Annotated[ArtifactStatus, typer.Option("--status")] = ArtifactStatus.CURRENT,
    agent: Annotated[str, typer.Option("--agent")] = "",
    content: Annotated[str | None, typer.Option("--content")] = None,
) -> None:
    """Register or update an artifact."""
    emit_result(
        operations.artifact_register(
            item_id=item_id,
            artifact_type=artifact_type.value,
            artifact_id=artifact_id,
            status=status.value,
            agent=agent,
            content=content,
        )
    )


@app.command("list")
def list_artifacts(
    item_id: Annotated[str, typer.Option("--item-id")],
    artifact_type: Annotated[ArtifactType | None, typer.Option("--artifact-type")] = None,
) -> None:
    """List artifacts registered for an item."""
    emit_result(
        operations.artifact_list(
            item_id=item_id, artifact_type=artifact_type.value if artifact_type is not None else None
        )
    )


@app.command("get")
def get(
    item_id: Annotated[str, typer.Option("--item-id")],
    artifact_type: Annotated[ArtifactType, typer.Option("--artifact-type")],
    artifact_id: Annotated[str | None, typer.Option("--artifact-id")] = None,
) -> None:
    """Get artifact metadata."""
    emit_result(operations.artifact_get(item_id=item_id, artifact_type=artifact_type.value, artifact_id=artifact_id))


@app.command("read")
def read(
    item_id: Annotated[str, typer.Option("--item-id")],
    artifact_type: Annotated[ArtifactType, typer.Option("--artifact-type")],
    artifact_id: Annotated[str | None, typer.Option("--artifact-id")] = None,
) -> None:
    """Read artifact content."""
    emit_result(operations.artifact_read(item_id=item_id, artifact_type=artifact_type.value, artifact_id=artifact_id))


@app.command("migrate")
def migrate(
    item_id: Annotated[str | None, typer.Option("--item-id")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    old_artifact_id: Annotated[str | None, typer.Option("--old-artifact-id")] = None,
    new_artifact_id: Annotated[str | None, typer.Option("--new-artifact-id")] = None,
) -> None:
    """Migrate artifacts or rename one manifest entry."""
    if (old_artifact_id is None) != (new_artifact_id is None):
        err("--old-artifact-id and --new-artifact-id must be provided together")
    if old_artifact_id is not None and item_id is None:
        err("--item-id is required when renaming an artifact")
    emit_result(
        operations.artifact_migrate(
            item_id=item_id, dry_run=dry_run, old_artifact_id=old_artifact_id, new_artifact_id=new_artifact_id
        )
    )


__all__ = ["app"]
