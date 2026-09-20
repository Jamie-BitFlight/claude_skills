"""Shared data contracts for research backlink extraction and reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BacklinkModel(BaseModel):
    """Base contract that rejects undeclared fields."""

    model_config = ConfigDict(extra="forbid")


class CrossRefRow(BacklinkModel):
    """One parsed row from a Cross-References Markdown table."""

    entry_name: str
    link_path: str
    category: str
    relationship: str


class ScanSkip(BacklinkModel):
    """One file the vault scan could not fold into the graph, and why."""

    path: str = Field(description="Path of the skipped file, relative to the vault root.")
    reason: str = Field(description="Which phase dropped it: 'read', 'parse', or 'resolve'.")
    detail: str = Field(description="The originating exception rendered as text.")


class CrossReferenceScan(BacklinkModel):
    """A vault graph and the coverage evidence from the scan that built it."""

    graph: dict[Path, list[Path]] = Field(
        default_factory=dict, description="Adjacency list mapping each entry to the entries it cites."
    )
    skips: list[ScanSkip] = Field(
        default_factory=list, description="Every file dropped during the scan, in vault-walk order."
    )
    files_parsed: int = Field(default=0, description="Files structurally parsed by Marko during this scan.")
    cache_hits: int = Field(default=0, description="Files whose successful extraction came from the content cache.")


class BacklinkEdge(BacklinkModel):
    """One asymmetric source-to-target edge rendered relative to the vault."""

    source: str
    target: str


class CheckBacklinksReport(BacklinkModel):
    """Versioned machine-readable result of the check-backlinks command."""

    schema_version: Literal[1] = 1
    asymmetric_cross_references: int
    edges: list[BacklinkEdge]
    scan_skipped_files: int
    skips: list[ScanSkip]
    files_parsed: int
    cache_hits: int
    backlinks_repaired: int | None = None
    backlinks_excluded: int | None = None
    verification_files_parsed: int | None = None
    verification_cache_hits: int | None = None
    remaining_asymmetric_cross_references: int | None = None
