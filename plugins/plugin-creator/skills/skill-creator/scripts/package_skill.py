#!/usr/bin/env python3
"""Create a ZIP using the local/client .skill extension convention.

The archive contents pass the portable Agent Skills frontmatter boundary, but
the .skill extension itself is not part of the portable specification.

Usage:
    python utils/package_skill.py <path/to/skill-folder> [output-directory]

Example:
    python utils/package_skill.py skills/public/my-skill
    python utils/package_skill.py skills/public/my-skill ./dist
"""

from __future__ import annotations

import logging
import sys
import zipfile
from pathlib import Path

from quick_validate import validate_skill

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Constants
MIN_ARGC = 2  # script name + skill-path (output-dir is optional)


def validate_inputs(skill_path: str, output_dir: str | None) -> tuple[bool, str | None]:
    """Validate command-line inputs.

    Args:
        skill_path: Path to skill folder
        output_dir: Optional output directory

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not skill_path.strip():
        return False, "Skill path cannot be empty"

    # Check for path traversal attempts
    if ".." in Path(skill_path).parts:
        return False, "Path traversal not allowed"

    # Validate output directory if provided
    if output_dir:
        if not output_dir.strip():
            return False, "Output directory cannot be empty"
        try:
            output_path = Path(output_dir).resolve()
            if output_path.exists() and not output_path.is_dir():
                return (False, f"Output path exists but is not a directory: {output_path}")
        except (ValueError, OSError) as e:
            return False, f"Invalid output directory: {e}"

    return True, None


def package_skill(skill_path: str | Path, output_dir: str | Path | None = None) -> Path | None:
    """Package a skill folder into a .skill file.

    Args:
        skill_path: Path to the skill folder (must exist and contain SKILL.md)
        output_dir: Optional output directory for the .skill file (defaults to current directory)

    Returns:
        Path to the created .skill file, or None if validation fails or skill folder invalid

    Raises:
        OSError: If file system operations fail during zip creation

    Note:
        Runs strict portable Agent Skills validation before packaging. Claude Code runtime
        extension fields are rejected because upload/API package boundaries hard-fail them.
    """
    skill_path = Path(skill_path).resolve()

    # Validate skill folder exists
    if not skill_path.exists():
        print(f"❌ Error: Skill folder not found: {skill_path}")
        return None

    if not skill_path.is_dir():
        print(f"❌ Error: Path is not a directory: {skill_path}")
        return None

    # Validate SKILL.md exists
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        print(f"❌ Error: SKILL.md not found in {skill_path}")
        return None

    # Run validation before packaging
    print("🔍 Validating skill...")
    valid, message = validate_skill(skill_path)
    if not valid:
        print(f"❌ Validation failed: {message}")
        print("   Please fix the validation errors before packaging.")
        return None
    print(f"✅ {message}\n")

    # Determine output location
    skill_name = skill_path.name
    if output_dir:
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path.cwd()

    skill_filename = output_path / f"{skill_name}.skill"

    # Create the .skill file (zip format)
    try:
        with zipfile.ZipFile(skill_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Walk through the skill directory
            for file_path in skill_path.rglob("*"):
                if file_path.is_file():
                    # Calculate the relative path within the zip
                    arcname = file_path.relative_to(skill_path.parent)
                    zipf.write(file_path, arcname)
                    print(f"  Added: {arcname}")
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile):
        logger.exception("Error creating .skill file")
        return None
    else:
        print(f"\n✅ Successfully packaged skill to: {skill_filename}")
        return skill_filename


def main() -> None:
    """Execute skill packaging from command line arguments.

    Expected format: package_skill.py <path/to/skill-folder> [output-directory]

    Exits:
        1: Invalid arguments, validation failed, or packaging error
        0: Skill packaged successfully
    """
    if len(sys.argv) < MIN_ARGC:
        print("Usage: python utils/package_skill.py <path/to/skill-folder> [output-directory]")
        print("\nExample:")
        print("  python utils/package_skill.py skills/public/my-skill")
        print("  python utils/package_skill.py skills/public/my-skill ./dist")
        sys.exit(1)

    skill_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > MIN_ARGC else None

    print(f"📦 Packaging skill: {skill_path}")
    if output_dir:
        print(f"   Output directory: {output_dir}")
    print()

    result = package_skill(skill_path, output_dir)

    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
