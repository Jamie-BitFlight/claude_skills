"""Run the T1 named AST mutants against public-seam tests."""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
import tempfile
from itertools import starmap
from pathlib import Path

PLUGIN = Path(__file__).parents[1]
BOUNDED_RUNNER = PLUGIN.parents[1] / "scripts" / "run_bounded.py"
MUTANT_TIMEOUT_SECONDS = 120
TIMEOUT_EXIT_CODE = 124
TEST = "tests_sam/test_merge_train_t1.py"
AMENDMENT_TEST = "tests_sam/test_merge_train_t1_amendment.py"
AMENDMENT_CASES = {
    "test_f02_replace_refuses_active_registered_attempt",
    "test_f02_import_replace_invalidates_inactive_registration",
    "test_f03_f08_deleted_binding_cannot_authorize_open_attempt",
    "test_f08_cross_copied_event_and_projection_reject_against_frozen_member",
    "test_f02_no_group_judge_pending_work_blocks_every_replacement_route",
    "test_s1_active_registration_refuses_dispatch_revision_only_drift",
}


class ReplaceIfTest(ast.NodeTransformer):
    """Replace one matching conditional with a constant false or true value."""

    def __init__(self, fragment: str, value: bool) -> None:
        self.fragment = fragment
        self.value = value
        self.changed = 0

    def visit_If(self, node: ast.If) -> ast.AST:
        """Mutate the matching conditional.

        Returns:
            The visited conditional.
        """
        self.generic_visit(node)
        if self.fragment in ast.unparse(node.test):
            node.test = ast.Constant(self.value)
            self.changed += 1
        return node


class RemoveCallStatement(ast.NodeTransformer):
    """Remove one standalone call carrying a named fragment."""

    def __init__(self, fragment: str) -> None:
        self.fragment = fragment
        self.changed = 0

    def visit_Expr(self, node: ast.Expr) -> ast.AST | None:
        """Remove the matching expression.

        Returns:
            None for the selected expression, otherwise the visited expression.
        """
        if self.changed == 0 and self.fragment in ast.unparse(node):
            self.changed += 1
            return None
        return self.generic_visit(node)


class RemoveStateRelease(ast.NodeTransformer):
    """Replace state-transition reservation release with no events."""

    def __init__(self) -> None:
        self.in_state = False
        self.changed = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        """Track the state function while visiting assignments.

        Returns:
            The visited function.
        """
        previous = self.in_state
        self.in_state = node.name == "state"
        self.generic_visit(node)
        self.in_state = previous
        return node

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        """Remove the selected release effect.

        Returns:
            The visited assignment.
        """
        if self.in_state and "release_reservations" in ast.unparse(node.value):
            node.value = ast.List(elts=[], ctx=ast.Load())
            self.changed += 1
        return self.generic_visit(node)


class RemoveFoldEffect(ast.NodeTransformer):
    """Make the reservation-release fold ignore its event."""

    def __init__(self) -> None:
        self.changed = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        """Replace the selected fold body.

        Returns:
            The visited function.
        """
        if node.name == "fold_merge_reservation_released":
            node.body = [ast.Pass()]
            self.changed += 1
            return node
        return self.generic_visit(node)


class RemoveAtomicBoundary(ast.NodeTransformer):
    """Flatten the private registered-dispatch transaction."""

    def __init__(self) -> None:
        self.changed = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        """Remove the selected transaction context.

        Returns:
            The visited function.
        """
        if node.name != "_dispatch_registered":
            return self.generic_visit(node)
        for index, statement in enumerate(node.body):
            if isinstance(statement, ast.With) and "store.transaction" in ast.unparse(statement.items[0].context_expr):
                node.body[index : index + 1] = statement.body
                self.changed += 1
                break
        return node


class RemoveUniqueIndex(ast.NodeTransformer):
    """Change the active reservation index from unique to ordinary."""

    def __init__(self) -> None:
        self.changed = 0

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        """Mutate the selected SQL literal.

        Returns:
            The replacement literal or the original node.
        """
        if (
            isinstance(node.value, str)
            and "CREATE UNIQUE INDEX IF NOT EXISTS ux_merge_reservations_active_group" in node.value
        ):
            self.changed += 1
            return ast.copy_location(ast.Constant(node.value.replace("CREATE UNIQUE INDEX", "CREATE INDEX", 1)), node)
        return node


MUTANTS: tuple[tuple[str, str, ast.NodeTransformer, str], ...] = (
    (
        "F01-remove-definition-equality",
        "dh_core/merge_train.py",
        ReplaceIfTest("str(row['dispatch_plan_digest']) == definition_digest", True),
        "test_s1_active_registration_refuses_dispatch_revision_only_drift",
    ),
    (
        "F01-remove-ledger-disagreement-check",
        "dh_core/merge_train.py",
        RemoveCallStatement("self.validate_definition"),
        "test_f01_registration_rejects_omitted_or_mismatched_resource",
    ),
    (
        "F02-remove-registered-replacement-active-check",
        "dh_core/ledger/port.py",
        ReplaceIfTest("train is not None and", False),
        "test_f02_no_group_judge_pending_work_blocks_every_replacement_route",
    ),
    (
        "F02-remove-invalidation-effect",
        "dh_core/ledger/port.py",
        RemoveCallStatement("invalidate_registered_generation"),
        "test_f02_import_replace_invalidates_inactive_registration",
    ),
    (
        "F08-accept-open-attempt-without-binding",
        "dh_core/ledger/transitions.py",
        ReplaceIfTest("exact and reservation", False),
        "test_f03_f08_deleted_binding_cannot_authorize_open_attempt",
    ),
    (
        "F03-bypass-raw-dispatch-guard",
        "dh_core/ledger/transitions.py",
        RemoveCallStatement("require_raw_dispatch_allowed(conn, plan, task)"),
        "test_f03_raw_dispatch_refuses_registered_task_without_opening_attempt",
    ),
    (
        "F03-remove-generation-check",
        "dh_core/ledger/transitions.py",
        ReplaceIfTest("int(train['generation']) != generation", False),
        "test_f03_stale_generation_cannot_dispatch",
    ),
    (
        "F03-remove-conflict-check",
        "dh_core/ledger/transitions.py",
        ReplaceIfTest("occupied is not None", False),
        "test_f03_registered_dispatch_reserves_conflict_group_atomically",
    ),
    (
        "F03-split-dispatch-transaction",
        "dh_core/ledger/transitions.py",
        RemoveAtomicBoundary(),
        "test_f03_reservation_failure_rolls_back_opened_attempt",
    ),
    (
        "F03-remove-unique-index",
        "dh_core/ledger/store.py",
        RemoveUniqueIndex(),
        "test_f03_schema_has_structural_active_group_uniqueness",
    ),
    (
        "F05-remove-coupled-release",
        "dh_core/ledger/transitions.py",
        RemoveStateRelease(),
        "test_f05_terminal_transition_releases_exact_attempt_and_group_is_reusable",
    ),
    (
        "F18-remove-release-fold-effect",
        "dh_core/ledger/store.py",
        RemoveFoldEffect(),
        "test_f18_rebuild_matches_independent_reservation_fold",
    ),
    (
        "F08-skip-frozen-member-binding-check",
        "dh_core/ledger/store.py",
        ReplaceIfTest("expected != actual", False),
        "test_f08_cross_copied_event_and_projection_reject_against_frozen_member",
    ),
    (
        "F24-remove-host-marker-check",
        "dh_core/ledger/transitions.py",
        ReplaceIfTest("str(train['authority_host_id']) != authority_host_id", False),
        "test_f24_host_marker_refuses_before_dispatch_mutation",
    ),
)


def mutate(path: Path, transformer: ast.NodeTransformer) -> None:
    """Apply one AST transformer and require exactly one changed node."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    transformed = transformer.visit(tree)
    changed = getattr(transformer, "changed", 0)
    if changed != 1:
        msg = f"{transformer.__class__.__name__} changed {changed} nodes in {path}"
        raise RuntimeError(msg)
    ast.fix_missing_locations(transformed)
    path.write_text(ast.unparse(transformed) + "\n", encoding="utf-8")


def run_mutant(name: str, relative: str, transformer: ast.NodeTransformer, test_name: str) -> bool:
    """Run one mutant in a copied plugin tree.

    Returns:
        True when its assigned test kills it.
    """
    with tempfile.TemporaryDirectory(prefix="dh-t1-mutant-") as directory:
        copied = Path(directory) / "development-harness"
        shutil.copytree(PLUGIN, copied)
        mutate(copied / relative, transformer)
        config = copied / "pytest.ini"
        config.write_text("[pytest]\n", encoding="utf-8")
        test_file = AMENDMENT_TEST if test_name in AMENDMENT_CASES else TEST
        completed = subprocess.run(
            [
                sys.executable,
                str(BOUNDED_RUNNER),
                "--timeout-seconds",
                str(MUTANT_TIMEOUT_SECONDS),
                "--",
                sys.executable,
                "-m",
                "pytest",
                "-c",
                str(config),
                "-p",
                "no:cacheprovider",
                "--strict-config",
                "-W",
                "error",
                f"{copied / test_file}::{test_name}",
            ],
            cwd=copied,
            env={**os.environ, "PYTHONPATH": str(copied)},
            capture_output=True,
            text=True,
            check=False,
        )
        outcome = (
            "TIMEOUT" if completed.returncode == TIMEOUT_EXIT_CODE else "KILLED" if completed.returncode else "SURVIVED"
        )
        print(f"MUTANT {name}: {outcome}")
        print(completed.stdout, end="")
        print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode not in {0, TIMEOUT_EXIT_CODE}


def main() -> int:
    """Run every named mutant and fail when any survives.

    Returns:
        Zero only when every mutant is killed.
    """
    results = list(starmap(run_mutant, MUTANTS))
    print(f"mutation score: {sum(results)}/{len(results)} killed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
