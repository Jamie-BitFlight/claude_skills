#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21.0"]
# ///
"""Validate Python shebang compliance using the 4-rule decision system.

This tool validates Python scripts for proper shebang usage based on:
- Rule 1: Python shebang for stdlib-only executable scripts
- Rule 2: Python shebang for package executables
- Rule 3: UV shebang for scripts with external dependencies
- Rule 4: No shebang for non-executable files

It checks PEP 723 compliance, execute bits, and provides auto-fix capabilities.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import typer
from rich import box
from rich.console import Console
from rich.measure import Measurement
from rich.table import Table

console = Console()
app = typer.Typer(help="Validate Python shebang compliance using 4-rule decision system")


# Valid shebang patterns
PYTHON_SHEBANG = "#!/usr/bin/env python3"
UV_SHEBANG = "#!/usr/bin/env -S uv --quiet run --active --script"

# Regex patterns
UV_SHEBANG_PATTERN = re.compile(r"^#!/usr/bin/env.* uv .*")
PYTHON_SHEBANG_PATTERN = re.compile(r"^#!/.*(/| )?python\d?")

RULE_STDLIB_SCRIPT = 1
RULE_PACKAGE_EXECUTABLE = 2
RULE_UV_SCRIPT = 3
RULE_NO_SHEBANG = 4

EXECUTABLE_RULES = {RULE_STDLIB_SCRIPT, RULE_PACKAGE_EXECUTABLE, RULE_UV_SCRIPT}

MAX_SHEBANG_PREVIEW = 40


@dataclass
class RuleEvaluation:
    """Result of evaluating a single rule's conditions.

    Args:
        rule_number: Which rule (1-4) was evaluated
        conditions_met: List of boolean results for each condition
        is_applicable: Whether this rule applies to the file
        reason: Explanation of why rule does/doesn't apply
    """

    rule_number: int
    conditions_met: list[bool]
    is_applicable: bool
    reason: str


@dataclass
class ValidationResult:
    """Complete validation result for a file.

    Args:
        current_shebang: Actual shebang line or "none"
        pep723_dependencies: Set of package names from PEP 723 metadata
        external_package_count: Number of external packages detected
        stdlib_imports: Set of stdlib module imports
        external_imports: Set of external module imports
        rule_evaluations: Results from evaluating all 4 rules
        applicable_rule: Which rule number applies (1-4)
        applicable_reason: Why that rule applies
        is_executable: Whether file has execute bit set
        is_correct: Whether shebang matches expected pattern
        expected_shebang: What the shebang should be
        errors: List of error messages
    """

    current_shebang: str
    pep723_dependencies: set[str]
    external_package_count: int
    stdlib_imports: set[str]
    external_imports: set[str]
    rule_evaluations: list[RuleEvaluation]
    applicable_rule: int
    applicable_reason: str
    is_executable: bool
    is_correct: bool
    expected_shebang: str
    errors: list[str]


def get_stdlib_modules() -> frozenset[str]:
    """Get standard library module names for the current Python version.

    Returns:
        Frozen set of standard library module names.
    """
    return sys.stdlib_module_names


def extract_imports(content: str) -> set[str]:
    """Extract all imported module names from Python code.

    Only extracts imports from actual code, not comments.

    Args:
        content: Python source code

    Returns:
        Set of base module names (e.g., 'os', 'pathlib', 'typer')
    """
    imports = set()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        # If syntax error, do basic regex extraction as fallback
        import_pattern = re.compile(r"^\s*(?:from\s+(\S+)|import\s+(\S+))", re.MULTILINE)
        for match in import_pattern.finditer(content):
            module = match.group(1) or match.group(2)
            if module:
                base_module = module.split(".")[0]
                imports.add(base_module)
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                base_module = alias.name.split(".")[0]
                imports.add(base_module)
        elif isinstance(node, ast.ImportFrom) and node.module:
            base_module = node.module.split(".")[0]
            imports.add(base_module)

    return imports


def extract_pep723_dependencies(content: str) -> tuple[bool, set[str]]:
    """Extract dependencies from PEP 723 metadata block.

    Handles both Unix (LF) and Windows (CRLF) line endings.

    Args:
        content: File content to parse

    Returns:
        Tuple of (has_pep723_block, set_of_normalized_package_names)
    """
    # Normalize line endings to handle Windows CRLF
    normalized_content = content.replace("\r\n", "\n")

    pep723_match = re.search(r"# /// script\n(.*?)\n# ///", normalized_content, re.DOTALL)
    if not pep723_match:
        return False, set()

    deps_match = re.search(r"dependencies\s*=\s*\[(.*?)\]", pep723_match.group(1), re.DOTALL)
    if not deps_match:
        return True, set()

    deps_text = deps_match.group(1)
    # Extract package names from dependency strings
    dependencies = set()
    for match in re.finditer(r'"([^"><=!\s]+)', deps_text):
        pkg = match.group(1)
        # Normalize package names (e.g., GitPython -> gitpython)
        dependencies.add(pkg.lower().replace("-", "_").replace(".", "_"))

    return True, dependencies


def normalize_import_to_package(import_name: str) -> str:
    """Map import names to package names.

    Args:
        import_name: Name as it appears in import statement

    Returns:
        Normalized package name for pip/uv
    """
    # Common import -> package mappings
    mappings = {
        "git": "gitpython",
        "semantic_release": "python_semantic_release",
        "yaml": "pyyaml",
        "cv2": "opencv_python",
        "sklearn": "scikit_learn",
        "PIL": "pillow",
        "Image": "pillow",
        "bs4": "beautifulsoup4",
        "dotenv": "python_dotenv",
        "_pytest": "pytest",
        "dateutil": "python_dateutil",
        "nacl": "pynacl",
        "OpenSSL": "pyopenssl",
        "jwt": "pyjwt",
        "serial": "pyserial",
        "magic": "python_magic",
        "markdown": "markdown",
        "lxml": "lxml",
    }

    normalized = import_name.lower().replace("-", "_").replace(".", "_")
    return mappings.get(import_name, normalized)


def is_part_of_package(file_path: Path) -> bool:
    """Check if file is part of an installed package.

    Searches parent directories for setup.py or pyproject.toml.

    Args:
        file_path: Path to file to check

    Returns:
        True if file is part of a package, False otherwise
    """
    current = file_path.resolve().parent
    root = Path("/")

    while current != root:
        if (current / "setup.py").exists() or (current / "pyproject.toml").exists():
            return True
        current = current.parent

    return False


def is_executable(file_path: Path) -> bool:
    """Check if file has execute permission.

    Args:
        file_path: Path to file to check

    Returns:
        True if file has execute bit set, False otherwise
    """
    return os.access(file_path, os.X_OK)


def evaluate_rule_1(is_exec: bool, has_external_deps: bool, uses_stdlib_only: bool) -> RuleEvaluation:
    """Evaluate Rule 1: Python shebang for stdlib-only executable scripts.

    Pattern: #!/usr/bin/env python3
    Conditions:
        1. File is executable
        2. Has no external dependencies
        3. Uses only Python standard library

    Args:
        is_exec: Whether file is executable
        has_external_deps: Whether file has external dependencies
        uses_stdlib_only: Whether file uses only stdlib

    Returns:
        RuleEvaluation with conditions and applicability
    """
    conditions = [is_exec, not has_external_deps, uses_stdlib_only]
    is_applicable = all(conditions)

    if is_applicable:
        reason = "File is executable, has no external dependencies, and uses only stdlib"
    else:
        unmet = []
        if not is_exec:
            unmet.append("not executable")
        if has_external_deps:
            unmet.append("has external dependencies")
        if not uses_stdlib_only:
            unmet.append("uses non-stdlib modules")
        reason = f"Does not meet conditions: {', '.join(unmet)}"

    return RuleEvaluation(rule_number=1, conditions_met=conditions, is_applicable=is_applicable, reason=reason)


def evaluate_rule_2(is_exec: bool, is_in_package: bool) -> RuleEvaluation:
    """Evaluate Rule 2: Python shebang for package executables.

    Pattern: #!/usr/bin/env python3
    Conditions:
        1. File is executable
        2. Part of installed package with setup.py or pyproject.toml

    Args:
        is_exec: Whether file is executable
        is_in_package: Whether file is part of a package

    Returns:
        RuleEvaluation with conditions and applicability
    """
    conditions = [is_exec, is_in_package]
    is_applicable = all(conditions)

    if is_applicable:
        reason = "File is executable and part of an installed package"
    else:
        unmet = []
        if not is_exec:
            unmet.append("not executable")
        if not is_in_package:
            unmet.append("not part of a package")
        reason = f"Does not meet conditions: {', '.join(unmet)}"

    return RuleEvaluation(rule_number=2, conditions_met=conditions, is_applicable=is_applicable, reason=reason)


def evaluate_rule_3(is_exec: bool, has_external_deps: bool) -> RuleEvaluation:
    """Evaluate Rule 3: UV shebang for scripts with external dependencies.

    Pattern: #!/usr/bin/env -S uv --quiet run --active --script
    Conditions:
        1. File is executable standalone script
        2. Requires external packages

    Args:
        is_exec: Whether file is executable
        has_external_deps: Whether file has external dependencies

    Returns:
        RuleEvaluation with conditions and applicability
    """
    conditions = [is_exec, has_external_deps]
    is_applicable = all(conditions)

    if is_applicable:
        reason = "File is executable standalone script with external dependencies"
    else:
        unmet = []
        if not is_exec:
            unmet.append("not executable")
        if not has_external_deps:
            unmet.append("no external dependencies")
        reason = f"Does not meet conditions: {', '.join(unmet)}"

    return RuleEvaluation(rule_number=3, conditions_met=conditions, is_applicable=is_applicable, reason=reason)


def evaluate_rule_4(is_exec: bool) -> RuleEvaluation:
    """Evaluate Rule 4: No shebang for non-executable files.

    Pattern: No shebang line
    Condition:
        1. File is library module OR imported by other code OR not directly executable

    Args:
        is_exec: Whether file is executable

    Returns:
        RuleEvaluation with conditions and applicability
    """
    conditions = [not is_exec]
    is_applicable = all(conditions)

    reason = "File is not executable (library/module)" if is_applicable else "File is executable"

    return RuleEvaluation(rule_number=4, conditions_met=conditions, is_applicable=is_applicable, reason=reason)


def determine_applicable_rule(file_path: Path, content: str) -> tuple[int, str, list[RuleEvaluation]]:
    """Determine which shebang rule applies to a file.

    Args:
        file_path: Path to the file
        content: File content

    Returns:
        Tuple of (rule_number, reason, list_of_all_evaluations)
    """
    # Gather file characteristics
    is_exec = is_executable(file_path)
    is_in_package = is_part_of_package(file_path)
    _has_pep723, pep723_deps = extract_pep723_dependencies(content)
    imports = extract_imports(content)
    stdlib = get_stdlib_modules()

    # Classify imports
    external_imports = imports - stdlib
    # Rich is included with Typer, not external
    if "rich" in external_imports and "typer" in pep723_deps:
        external_imports.discard("rich")

    has_external_deps = len(external_imports) > 0
    uses_stdlib_only = len(external_imports) == 0

    # Evaluate all rules
    rule1 = evaluate_rule_1(is_exec, has_external_deps, uses_stdlib_only)
    rule2 = evaluate_rule_2(is_exec, is_in_package)
    rule3 = evaluate_rule_3(is_exec, has_external_deps)
    rule4 = evaluate_rule_4(is_exec)

    evaluations = [rule1, rule2, rule3, rule4]

    # Determine which rule applies (priority order: 2, 3, 1, 4)
    # Rule 2 takes precedence over Rule 1 and 3 if file is in package
    if rule2.is_applicable:
        return 2, rule2.reason, evaluations
    if rule3.is_applicable:
        return 3, rule3.reason, evaluations
    if rule1.is_applicable:
        return 1, rule1.reason, evaluations
    if rule4.is_applicable:
        return 4, rule4.reason, evaluations
    # Fallback - should not happen but handle gracefully
    return 4, "No applicable rule found, defaulting to no shebang", evaluations


def get_expected_shebang(rule_number: int) -> str:
    """Get the expected shebang pattern for a rule.

    Args:
        rule_number: Rule number (1-4)

    Returns:
        Expected shebang string or "none" for Rule 4
    """
    match rule_number:
        case 1 | 2:
            return PYTHON_SHEBANG
        case 3:
            return UV_SHEBANG
        case 4:
            return "none"
        case _:
            return "none"


def diagnose_uv_shebang(shebang: str) -> list[str]:
    """Diagnose issues with a UV shebang line.

    Args:
        shebang: The shebang line to diagnose

    Returns:
        List of diagnostic messages
    """
    diagnostics: list[str] = []
    expected = UV_SHEBANG

    if shebang == expected:
        return diagnostics

    # Check for missing flags
    if "--quiet" not in shebang:
        diagnostics.append("Missing --quiet global flag (should come before 'run')")
    if "--active" not in shebang:
        diagnostics.append("Missing --active subcommand flag (should come after 'run')")
    if "--script" not in shebang:
        diagnostics.append("Missing --script subcommand flag (should come after 'run')")

    # Check for incorrect flag positions
    if "--quiet" in shebang and " run " in shebang:
        quiet_pos = shebang.index("--quiet")
        run_pos = shebang.index(" run ")
        if quiet_pos > run_pos:
            diagnostics.append("Flag ordering error: --quiet is a global flag and must come BEFORE 'run'")

    if "--active" in shebang and " run " in shebang:
        active_pos = shebang.index("--active")
        run_pos = shebang.index(" run ")
        if active_pos < run_pos:
            diagnostics.append("Flag ordering error: --active is a subcommand flag and must come AFTER 'run'")

    # Explain the pattern
    if diagnostics:
        diagnostics.extend((
            "",
            "Correct pattern: uv [GLOBAL_FLAGS] SUBCOMMAND [SUBCOMMAND_FLAGS]",
            "Global flags (--quiet) modify uv itself and come before subcommand",
            "Subcommand flags (--active, --script) modify 'run' and come after it",
        ))

    return diagnostics


def _analyze_content(file_path: Path, content: str) -> tuple[str, set[str], set[str], set[str], bool]:
    """Analyze a Python file's content for shebang/deps/import metadata.

    Args:
        file_path: Path to the file being analyzed.
        content: Full file content.

    Returns:
        Tuple of:
        - current_shebang ("none" if absent)
        - pep723_deps (normalized dependency names)
        - stdlib_imports
        - external_imports
        - is_executable (execute bit set)
    """
    lines = content.split("\n")
    current_shebang = lines[0] if lines and lines[0].startswith("#!") else "none"

    _has_pep723, pep723_deps = extract_pep723_dependencies(content)
    imports = extract_imports(content)
    stdlib = get_stdlib_modules()
    stdlib_imports = imports & stdlib
    external_imports = imports - stdlib

    # Rich is included with Typer
    if "rich" in external_imports and "typer" in pep723_deps:
        external_imports.discard("rich")

    return (current_shebang, pep723_deps, stdlib_imports, external_imports, is_executable(file_path))


def validate_file(file_path: Path) -> ValidationResult:
    """Validate a Python file's shebang compliance.

    Args:
        file_path: Path to Python script

    Returns:
        ValidationResult with complete analysis
    """
    if not file_path.exists():
        return ValidationResult(
            current_shebang="error",
            pep723_dependencies=set(),
            external_package_count=0,
            stdlib_imports=set(),
            external_imports=set(),
            rule_evaluations=[],
            applicable_rule=0,
            applicable_reason="File not found",
            is_executable=False,
            is_correct=False,
            expected_shebang="error",
            errors=[f"File not found: {file_path}"],
        )

    content = file_path.read_text(encoding="utf-8")
    (current_shebang, pep723_deps, stdlib_imports, external_imports, is_exec) = _analyze_content(file_path, content)
    external_package_count = len(external_imports)

    # Determine applicable rule
    rule_number, reason, evaluations = determine_applicable_rule(file_path, content)

    # Get expected shebang
    expected_shebang = get_expected_shebang(rule_number)

    # Check if current matches expected
    is_correct = current_shebang == expected_shebang

    # Gather errors
    errors: list[str] = []
    if not is_correct:
        errors.append(f"Incorrect shebang: expected '{expected_shebang}', got '{current_shebang}'")

        # Add detailed diagnostics for UV shebangs
        if rule_number == RULE_UV_SCRIPT and UV_SHEBANG_PATTERN.match(current_shebang):
            diag = diagnose_uv_shebang(current_shebang)
            errors.extend(diag)

    # Check execute bit alignment with rule
    if rule_number in EXECUTABLE_RULES and not is_exec:
        errors.append(f"Rule {rule_number} requires execute bit, but file is not executable")
    elif rule_number == RULE_NO_SHEBANG and is_exec:
        errors.append("Rule 4 (no shebang) applies, but file has execute bit set")

    return ValidationResult(
        current_shebang=current_shebang,
        pep723_dependencies=pep723_deps,
        external_package_count=external_package_count,
        stdlib_imports=stdlib_imports,
        external_imports=external_imports,
        rule_evaluations=evaluations,
        applicable_rule=rule_number,
        applicable_reason=reason,
        is_executable=is_exec,
        is_correct=is_correct,
        expected_shebang=expected_shebang,
        errors=errors,
    )


def format_validation_output(result: ValidationResult) -> str:
    """Format validation result in the mandatory 8-step format.

    Args:
        result: ValidationResult to format

    Returns:
        Formatted output string
    """
    output: list[str] = [f"1. Current shebang: {result.current_shebang}"]

    deps_list = ", ".join(sorted(result.pep723_dependencies)) if result.pep723_dependencies else "none"
    evidence = f" (imports: {', '.join(sorted(result.external_imports))})" if result.external_imports else ""
    stdlib_list = ", ".join(sorted(result.stdlib_imports)) if result.stdlib_imports else "none"
    external_list = ", ".join(sorted(result.external_imports)) if result.external_imports else "none"

    output.extend([
        f"2. PEP 723 metadata dependencies: {deps_list}",
        f"3. External package count: {result.external_package_count}{evidence}",
        "4. Import analysis:",
        f"   stdlib: {stdlib_list}",
        f"   external: {external_list}",
        "5. Rule condition evaluation:",
    ])
    for eval_result in result.rule_evaluations:
        conditions_str = " ".join(
            f"(condition {i + 1} {'MET' if cond else 'NOT MET'})" for i, cond in enumerate(eval_result.conditions_met)
        )
        output.append(f"   Rule {eval_result.rule_number}: {conditions_str}")

    exec_status = "executable" if result.is_executable else "not executable"
    verdict = "CORRECT" if result.is_correct and not result.errors else "INCORRECT"
    output.extend([
        f"6. Applicable rule: {result.applicable_rule} because {result.applicable_reason}",
        f"7. Execute bit: {exec_status}",
        f"8. Verdict: {verdict}",
    ])

    if result.errors:
        output.append("\nErrors:")
        output.extend(f"  - {error}" for error in result.errors)

    return "\n".join(output)


def auto_fix_file(file_path: Path, result: ValidationResult) -> bool:
    """Auto-fix a file's shebang and PEP 723 metadata.

    Args:
        file_path: Path to file to fix
        result: Validation result indicating what needs fixing

    Returns:
        True if fix was successful, False otherwise
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        needs_shebang = result.applicable_rule in EXECUTABLE_RULES
        needs_pep723 = result.applicable_rule == RULE_UV_SCRIPT
        needs_execute_bit = result.applicable_rule in EXECUTABLE_RULES

        # Remove existing shebang (if present)
        if lines and lines[0].startswith("#!"):
            lines = lines[1:]

        content_no_shebang = "\n".join(lines)

        # Remove existing PEP 723 block (if present)
        content_no_pep723 = re.sub(r"# /// script\n.*?\n# ///\n?", "", content_no_shebang, flags=re.DOTALL)
        content_no_pep723 = re.sub(r"\n{3,}", "\n\n", content_no_pep723)
        remaining_lines = content_no_pep723.split("\n")

        new_lines: list[str] = []
        if needs_shebang:
            new_lines.append(result.expected_shebang)

        if needs_pep723:
            new_lines.extend(("# /// script", '# requires-python = ">=3.11"'))
            if result.external_imports:
                new_lines.append("# dependencies = [")
                for imp in sorted(result.external_imports):
                    pkg_name = normalize_import_to_package(imp)
                    new_lines.append(f'#     "{pkg_name}>=0.1.0",')
                new_lines.append("# ]")
            else:
                new_lines.append("# dependencies = []")
            new_lines.append("# ///")

        new_lines.extend(remaining_lines)
        file_path.write_text("\n".join(new_lines), encoding="utf-8")

        if needs_execute_bit and not result.is_executable:
            file_path.chmod(file_path.stat().st_mode | 0o111)

        if result.applicable_rule == RULE_NO_SHEBANG and result.is_executable:
            file_path.chmod(file_path.stat().st_mode & ~0o111)

    except OSError as e:
        console.print(f"[red]ERROR: Failed to fix file: {e}[/red]")
        return False
    else:
        return True


def _get_table_width(table: Table) -> int:
    """Get the natural width of a table using a temporary wide console.

    Args:
        table: The Rich table to measure

    Returns:
        The width in characters needed to display the table
    """
    # Create a temporary console with very wide width
    temp_console = Console(width=9999)
    # Measure the table
    measurement = Measurement.get(temp_console, temp_console.options, table)
    return int(measurement.maximum)


@app.command()
def check(
    script_path: Annotated[
        Path,
        typer.Argument(
            help="Path to Python script to validate", exists=True, file_okay=True, dir_okay=False, readable=True
        ),
    ],
    fix: Annotated[bool, typer.Option("--fix", "-f", help="Auto-fix issues")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed output")] = False,
) -> None:
    """Validate Python shebang compliance using 4-rule decision system.

    Validates shebang pattern, PEP 723 metadata, and execute bit.
    With --fix flag, automatically corrects issues.
    """
    console.print(f"\n[bold]Validating:[/bold] {script_path}")
    console.print("-" * 70)

    # Validate
    result = validate_file(script_path)

    # Display in mandatory 8-step format
    if verbose:
        console.print(format_validation_output(result))
        console.print("-" * 70)

    # Apply fixes if requested
    if fix and not result.is_correct:
        console.print("\n[yellow]Applying fixes...[/yellow]")
        if auto_fix_file(script_path, result):
            console.print("[green]File fixed successfully[/green]")
            # Re-validate
            result = validate_file(script_path)
            console.print("\n[bold]After fix:[/bold]")
            console.print(format_validation_output(result))
        else:
            console.print("[red]Fix failed[/red]")
            raise typer.Exit(1)

    # Summary
    if result.is_correct:
        console.print("\n[green]:white_check_mark: CORRECT[/green]")
        console.print(f"Rule {result.applicable_rule} applies: {result.applicable_reason}")
        if result.expected_shebang != "none":
            console.print(f"Shebang: {result.expected_shebang}")
        raise typer.Exit(0)
    console.print("\n[red]:cross_mark: INCORRECT[/red]")
    console.print(f"Expected: {result.expected_shebang}")
    console.print(f"Got: {result.current_shebang}")

    if not verbose:
        console.print("\nRun with --verbose for detailed analysis")
    if not fix:
        console.print("Run with --fix to auto-correct issues")

    raise typer.Exit(1)


@app.command()
def batch(
    directory: Annotated[
        Path,
        typer.Argument(
            help="Directory to scan for Python scripts", exists=True, file_okay=False, dir_okay=True, readable=True
        ),
    ],
    pattern: Annotated[str, typer.Option("--pattern", "-p", help="Glob pattern for files")] = "*.py",
    fix: Annotated[bool, typer.Option("--fix", "-f", help="Auto-fix issues in all files")] = False,
) -> None:
    """Validate all Python scripts in a directory."""
    # Find all Python files
    files = list(directory.glob(pattern))
    if not files:
        console.print(f"[yellow]No files matching pattern '{pattern}' in {directory}[/yellow]")
        raise typer.Exit(0)

    # Create results table
    table = Table(title=f"Shebang Validation Results for {directory}", box=box.MINIMAL_DOUBLE_HEAD)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Rule", justify="center")
    table.add_column("Expected Shebang", style="yellow")
    table.add_column("Status", justify="center")

    total_files = 0
    correct_files = 0
    fixed_files = 0

    for file_path in sorted(files):
        if file_path.is_file():
            total_files += 1
            result = validate_file(file_path)

            # Attempt fix if requested
            if fix and not result.is_correct and auto_fix_file(file_path, result):
                fixed_files += 1
                result = validate_file(file_path)

            status = "[green]:white_check_mark:[/green]" if result.is_correct else "[red]:cross_mark:[/red]"

            expected = (
                result.expected_shebang[:MAX_SHEBANG_PREVIEW] + "..."
                if len(result.expected_shebang) > MAX_SHEBANG_PREVIEW
                else result.expected_shebang
            )

            table.add_row(file_path.name, str(result.applicable_rule), expected, status)

            if result.is_correct:
                correct_files += 1

    # Set table width to its natural size
    table_width = _get_table_width(table)
    table.width = table_width

    # Print with proper settings
    console.print(table, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)

    console.print(f"\nSummary: {correct_files}/{total_files} files correct")
    if fix:
        console.print(f"Fixed: {fixed_files} files")

    if correct_files < total_files and not fix:
        console.print("\n[yellow]Run with --fix to auto-correct issues[/yellow]")

    if correct_files < total_files:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
