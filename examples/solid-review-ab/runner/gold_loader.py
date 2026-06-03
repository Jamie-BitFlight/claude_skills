"""Gold-set loading and normalisation for the SOLID A/B experiment."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class GoldEntry:
    """One labelled location from the ground-truth gold set.

    Attributes:
        group: SOLID group letter (S/O/L/I/D).
        rule_id: Stable rule identifier from solid-rules.json (e.g. SRP-1).
        location: Normalised repo-relative path:line (e.g. corpus/cases/01.py:17).
        severity: critical | high | medium | low.
        kind: true_violation | decoy_false_positive | systematic_miss.
        note: Human-readable annotation explaining the entry.
    """

    group: str
    rule_id: str
    location: str
    severity: str
    kind: str
    note: str = ""


def load_gold(gold_path: Path) -> list[GoldEntry]:
    """Parse gold.json into a flat list of GoldEntry objects.

    Args:
        gold_path: Absolute or repo-relative path to gold.json.

    Returns:
        All gold entries across all case files, in file order.

    Raises:
        FileNotFoundError: When gold_path does not exist.
        KeyError: When a required field is absent from an entry.
    """
    raw: dict[str, list[dict[str, str]]] = json.loads(gold_path.read_text(encoding="utf-8"))
    entries: list[GoldEntry] = []
    for case_entries in raw.values():
        entries.extend(
            GoldEntry(
                group=e["group"],
                rule_id=e["rule_id"],
                location=e["location"],
                severity=e["severity"],
                kind=e["kind"],
                note=e.get("note", ""),
            )
            for e in case_entries
        )
    return entries


def positive_keys(gold: list[GoldEntry]) -> set[tuple[str, str]]:
    """Return the set of (group, location) keys for true_violation and systematic_miss entries.

    These are the keys an arm SHOULD report to score a TP.

    Args:
        gold: The full list of gold entries.

    Returns:
        Set of (group, normalised_location) tuples representing real defects.
    """
    return {(e.group, e.location) for e in gold if e.kind in {"true_violation", "systematic_miss"}}


def decoy_keys(gold: list[GoldEntry]) -> set[tuple[str, str]]:
    """Return the set of (group, location) keys for decoy_false_positive entries.

    An arm reporting any of these has been tricked by a false positive.

    Args:
        gold: The full list of gold entries.

    Returns:
        Set of (group, normalised_location) tuples representing decoy locations.
    """
    return {(e.group, e.location) for e in gold if e.kind == "decoy_false_positive"}
