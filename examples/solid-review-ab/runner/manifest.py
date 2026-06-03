"""Manifest loader for the judgement system.

Loads arms.yaml using ruamel.yaml and exposes typed dataclasses.
All ruamel.yaml CommentedMap/CommentedSeq types are fully resolved
inside this module — callers receive plain Python objects only.

Public API
----------
ArmType           — enum declaring whether an arm is single or ensemble
ArmEntry          — single arm declaration from the manifest
ModelRef          — model + role pair within an arm
ModelPrice        — input/output price per 1k tokens
Manifest          — top-level parsed manifest
load_manifest(path) -> Manifest
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from pathlib import Path


class ArmType(StrEnum):
    """Declarative arm classification validated at manifest load time.

    Drives scoring path selection in the CLI — never inferred from the
    filesystem.  Missing or invalid values in arms.yaml raise at load time
    so invalid manifests are caught before any arm is dispatched.

    Values:
        SINGLE: One agent produces findings/findings.md.
        ENSEMBLE: Multiple worker agents produce findings/workers/worker-*.md.
    """

    SINGLE = "single"
    ENSEMBLE = "ensemble"


@dataclass
class ModelRef:
    """One model entry within an arm's models list.

    Attributes:
        id: Model identifier used to look up prices (must match a key in
            Manifest.prices).
        role: Descriptive label for human display (e.g. "primary", "worker").
    """

    id: str
    role: str


@dataclass
class ArmEntry:
    """One arm declaration from the manifest.

    Attributes:
        name: Human-readable arm label used in tables and CLI output.
        dir: Arm root directory, resolved to an absolute path by load_manifest.
        enabled: When False the arm is skipped without removing the entry.
        arm_type: Explicit arm classification — drives scoring path selection.
            Must be declared in arms.yaml; never inferred from the filesystem.
        models: Ordered list of model references used for cost accounting.
    """

    name: str
    dir: Path
    enabled: bool
    arm_type: ArmType
    models: list[ModelRef] = field(default_factory=list)


@dataclass
class ModelPrice:
    """Per-model token pricing.

    Attributes:
        input_per_1k: Cost in USD per 1,000 input tokens.
        output_per_1k: Cost in USD per 1,000 output tokens.
    """

    input_per_1k: float
    output_per_1k: float


@dataclass
class Manifest:
    """Fully parsed and resolved manifest.

    Attributes:
        arms: All arm entries (enabled and disabled).
        prices: Mapping from model id to its price entry.
        manifest_path: Absolute path to the source arms.yaml file.
    """

    arms: list[ArmEntry]
    prices: dict[str, ModelPrice]
    manifest_path: Path

    def enabled_arms(self) -> list[ArmEntry]:
        """Return only the arms with enabled=True, in manifest order.

        Returns:
            List of ArmEntry where enabled is True.
        """
        return [arm for arm in self.arms if arm.enabled]


def load_manifest(path: Path) -> Manifest:
    """Load and validate arms.yaml, returning a fully typed Manifest.

    Resolves each arm's dir relative to the manifest file's parent directory.
    All ruamel.yaml types are converted to plain Python objects before return.

    Args:
        path: Absolute or relative path to arms.yaml.

    Returns:
        Parsed Manifest with resolved arm directories.

    Raises:
        FileNotFoundError: When the manifest file does not exist.
        KeyError: When a required field (e.g. arm_type) is missing from an arm entry.
        ValueError: When arm_type has an unrecognised value, or a model id has no
            price entry in the manifest prices table.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Manifest not found: {path}")

    yaml = YAML()
    yaml.preserve_quotes = True
    raw = yaml.load(path)

    experiment_root = path.parent

    prices: dict[str, ModelPrice] = {}
    for model_id, price_raw in (raw.get("prices") or {}).items():
        prices[str(model_id)] = ModelPrice(
            input_per_1k=float(price_raw["input_per_1k"]), output_per_1k=float(price_raw["output_per_1k"])
        )

    arms: list[ArmEntry] = []
    for raw_arm in raw.get("arms") or []:
        model_refs: list[ModelRef] = []
        for m in raw_arm.get("models") or []:
            model_id = str(m["id"])
            if model_id not in prices:
                raise ValueError(
                    f"Arm '{raw_arm['name']}' references model '{model_id}' "
                    f"which has no entry in the manifest prices table."
                )
            model_refs.append(ModelRef(id=model_id, role=str(m["role"])))

        arm_dir = experiment_root / str(raw_arm["dir"])
        arm_name = str(raw_arm["name"])
        try:
            arm_type = ArmType(str(raw_arm["arm_type"]))
        except ValueError as exc:
            raise ValueError(
                f"Arm '{arm_name}' has invalid arm_type value: {exc}. Valid values are: {[t.value for t in ArmType]}"
            ) from exc
        arms.append(
            ArmEntry(
                name=arm_name,
                dir=arm_dir.resolve(),
                enabled=bool(raw_arm.get("enabled", True)),
                arm_type=arm_type,
                models=model_refs,
            )
        )

    return Manifest(arms=arms, prices=prices, manifest_path=path.resolve())
