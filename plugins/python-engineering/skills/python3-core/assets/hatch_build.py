"""Custom hatchling build hook for binary compilation.

This hook runs before the build process to compile platform-specific binaries
if build scripts are present in the project.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - subprocess required for build script execution, all calls use list form (not shell=True)
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class BinaryBuildHook(BuildHookInterface[Any]):
    """Build hook that runs binary compilation scripts before packaging.

    This hook checks for the following scripts in order:
    1. scripts/build-binaries.sh
    2. scripts/build-binaries.py

    If either script exists, it is executed before the build process.
    If neither exists, the hook silently continues without error.
    """

    PLUGIN_NAME = "binary-build"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Run binary build scripts if they exist.

        This method is called immediately before each build. It checks for
        build scripts and executes them if found.

        Args:
            version: The version string for this build
            build_data: Build configuration dictionary that will be passed to the build target
        """
        # Check for shell script first
        shell_script = Path(self.root) / "scripts" / "build-binaries.sh"
        if shell_script.exists() and shell_script.is_file():
            self._run_shell_script(shell_script)
            return

        # Fallback to Python script
        python_script = Path(self.root) / "scripts" / "build-binaries.py"
        if python_script.exists() and python_script.is_file():
            self._run_python_script(python_script)
            return

        # No scripts found - silently continue
        self.app.display_info("No binary build scripts found, skipping binary compilation")

    def _run_shell_script(self, script_path: Path) -> None:
        """Execute a shell script for binary building.

        Args:
            script_path: Path to the shell script to execute

        Raises:
            subprocess.CalledProcessError: If the script exits with non-zero status
        """
        self.app.display_info(f"Running binary build script: {script_path}")

        # Get full path to bash executable for security (B607)
        bash_path = shutil.which("bash")
        if not bash_path:
            msg = "bash executable not found in PATH"
            raise RuntimeError(msg)

        try:
            result = subprocess.run(  # nosec B603 - using command list with full path, not shell=True
                [bash_path, str(script_path)], cwd=self.root, capture_output=True, text=True, check=True
            )
            if result.stdout:
                self.app.display_info(result.stdout)
            if result.stderr:
                self.app.display_warning(result.stderr)
        except subprocess.CalledProcessError as e:
            self.app.display_error(f"Binary build script failed with exit code {e.returncode}")
            if e.stdout:
                self.app.display_info(f"stdout: {e.stdout}")
            if e.stderr:
                self.app.display_error(f"stderr: {e.stderr}")
            raise

    def _run_python_script(self, script_path: Path) -> None:
        """Execute a Python script for binary building.

        Args:
            script_path: Path to the Python script to execute

        Raises:
            subprocess.CalledProcessError: If the script exits with non-zero status
        """
        self.app.display_info(f"Running binary build script: {script_path}")

        # Get full path to python3 executable for security (B607)
        python_path = shutil.which("python3")
        if not python_path:
            msg = "python3 executable not found in PATH"
            raise RuntimeError(msg)

        try:
            result = subprocess.run(  # nosec B603 - using command list with full path, not shell=True
                [python_path, str(script_path)], cwd=self.root, capture_output=True, text=True, check=True
            )
            if result.stdout:
                self.app.display_info(result.stdout)
            if result.stderr:
                self.app.display_warning(result.stderr)
        except subprocess.CalledProcessError as e:
            self.app.display_error(f"Binary build script failed with exit code {e.returncode}")
            if e.stdout:
                self.app.display_info(f"stdout: {e.stdout}")
            if e.stderr:
                self.app.display_error(f"stderr: {e.stderr}")
            raise
