"""Integration tests for lazy migration backend detection.

Tests verify the resolution order for ``create_task_backend()``:

    TASKBACKEND env var > .dh/config.yaml > default "local"

And verify that ``create_task_backend(name=...)`` routes correctly to the
appropriate backend, simulating what backend_ref detection in a plan YAML
would produce.

No asyncio — all tests are synchronous. asyncio_mode = "auto" in pyproject.toml.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
import sam_schema.core.task_config as task_config_module
from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
from sam_schema.core.backends.memory import InMemoryTaskProvider
from sam_schema.core.task_config import create_task_backend, reset_task_config

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_config() -> Generator[None, None, None]:
    """Clear _active_config before and after each test.

    Ensures that the module-level TaskConfig singleton does not leak between
    tests. reset_task_config() sets _active_config = None so the next
    get_task_config() call raises RuntimeError rather than returning a stale
    config from a previous test.

    Yields:
        None (setup/teardown only).
    """
    reset_task_config()
    yield
    reset_task_config()


# ---------------------------------------------------------------------------
# TestLazyMigration
# ---------------------------------------------------------------------------


class TestLazyMigration:
    """Tests for backend_ref detection and migration routing."""

    def test_plan_without_backend_ref_uses_local(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A plan YAML without backend_ref routes through LocalYamlTaskProvider.

        When no TASKBACKEND env var is set and no .dh/config.yaml is found,
        create_task_backend() returns the default LocalYamlTaskProvider. This is
        the "plan without backend_ref" path — the plan has not been migrated to a
        remote backend.

        Arrange: clear TASKBACKEND env var; stub DHConfig to the subsystem default.
        Act: call create_task_backend() with no arguments.
        Assert: returned backend is a LocalYamlTaskProvider instance.
        """
        # Arrange
        monkeypatch.delenv("TASKBACKEND", raising=False)
        # create_task_backend delegates the whole chain to DHConfig; stub it to the
        # subsystem default so this test exercises the no-config fall-through.
        monkeypatch.setattr(task_config_module.DHConfig, "get_backend", lambda self, subsystem: "local")

        # Act
        backend = create_task_backend()

        # Assert
        assert isinstance(backend, LocalYamlTaskProvider)

    def test_plan_with_backend_ref_routes_to_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A plan YAML with backend_ref field routes through the specified backend.

        When a plan YAML contains backend_ref (e.g., ``"memory://..."``), the
        detection logic extracts the backend name and calls
        ``create_task_backend(name)``.  This test verifies that passing
        ``name="memory"`` — as backend_ref detection would do — returns an
        InMemoryTaskProvider instead of the default local backend.

        Arrange: clear TASKBACKEND env var; stub DHConfig to the subsystem default.
        Act: call create_task_backend(name="memory").
        Assert: returned backend is an InMemoryTaskProvider instance.
        """
        # Arrange
        monkeypatch.delenv("TASKBACKEND", raising=False)
        # create_task_backend delegates the whole chain to DHConfig; stub it to the
        # subsystem default so this test exercises the no-config fall-through.
        monkeypatch.setattr(task_config_module.DHConfig, "get_backend", lambda self, subsystem: "local")

        # Act — simulates backend_ref detection resolving to "memory"
        backend = create_task_backend(name="memory")

        # Assert
        assert isinstance(backend, InMemoryTaskProvider)

    def test_taskbackend_toml_overrides_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """config.yaml task backend setting selects the backend.

        When ``.dh/config.yaml`` declares ``task.backend: memory`` (resolved via
        DHConfig), it overrides the default ``"local"`` backend.

        Arrange: write .dh/config.yaml with task.backend=memory to tmp_path;
                 mock dh_config._dh_paths to return tmp_path as project root;
                 clear TASKBACKEND env var.
        Act: call create_task_backend() with no arguments.
        Assert: returned backend is InMemoryTaskProvider.
        """
        import dh_config as _dh_config_mod

        # Arrange — write YAML config to the mocked project .dh/ dir
        dh_dir = tmp_path / ".dh"
        dh_dir.mkdir()
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        with (dh_dir / "config.yaml").open("w", encoding="utf-8") as fh:
            yaml.dump({"task": {"backend": "memory"}}, fh)

        monkeypatch.delenv("TASKBACKEND", raising=False)

        mock_dh = MagicMock()
        mock_dh.git_project_root.return_value = tmp_path
        mock_dh._dh_user_root.return_value = tmp_path / "home" / ".dh"
        mock_dh.project_dh_dir.return_value = dh_dir
        (tmp_path / "home" / ".dh").mkdir(parents=True)
        monkeypatch.setattr(_dh_config_mod, "_dh_paths", mock_dh)

        # Act
        backend = create_task_backend()

        # Assert
        assert isinstance(backend, InMemoryTaskProvider)

    def test_env_var_overrides_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """TASKBACKEND env var takes precedence over config.yaml.

        When ``TASKBACKEND="memory"`` is set and ``.dh/config.yaml`` declares
        ``task.backend: local``, the env var wins.  Resolution order:
        env var > config.yaml > default ``"local"``.

        Arrange: write .dh/config.yaml with task.backend=local to tmp_path;
                 set TASKBACKEND="memory" via monkeypatch;
                 mock dh_config._dh_paths to return tmp_path.
        Act: call create_task_backend() with no arguments.
        Assert: returned backend is InMemoryTaskProvider (env var wins over config).
        """
        import dh_config as _dh_config_mod

        # Arrange — config says "local", env var says "memory"
        dh_dir = tmp_path / ".dh"
        dh_dir.mkdir()
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        with (dh_dir / "config.yaml").open("w", encoding="utf-8") as fh:
            yaml.dump({"task": {"backend": "local"}}, fh)

        monkeypatch.setenv("TASKBACKEND", "memory")

        mock_dh = MagicMock()
        mock_dh.git_project_root.return_value = tmp_path
        mock_dh._dh_user_root.return_value = tmp_path / "home" / ".dh"
        mock_dh.project_dh_dir.return_value = dh_dir
        (tmp_path / "home" / ".dh").mkdir(parents=True)
        monkeypatch.setattr(_dh_config_mod, "_dh_paths", mock_dh)

        # Act
        backend = create_task_backend()

        # Assert — TASKBACKEND env var overrides config.yaml
        assert isinstance(backend, InMemoryTaskProvider)

    def test_mixed_plans_different_backends(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Plans in the same directory can use different backends via backend_ref.

        When a project has plans at different migration stages, each plan routes
        through the backend indicated by its backend_ref field.  Plans without
        backend_ref use the local default; plans with a backend_ref (e.g.
        ``"memory://..."``) route to the named backend.

        Arrange: clear TASKBACKEND env var; stub DHConfig to the subsystem default.
        Act: call create_task_backend() without a name (plan without backend_ref)
             and create_task_backend("memory") (plan with backend_ref).
        Assert: first call returns LocalYamlTaskProvider;
                second call returns InMemoryTaskProvider;
                the two instances are distinct objects.
        """
        # Arrange
        monkeypatch.delenv("TASKBACKEND", raising=False)
        # create_task_backend delegates the whole chain to DHConfig; stub it to the
        # subsystem default so this test exercises the no-config fall-through.
        monkeypatch.setattr(task_config_module.DHConfig, "get_backend", lambda self, subsystem: "local")

        # Act — two plans in the same directory routed to different backends
        local_backend = create_task_backend()  # plan without backend_ref → default local
        memory_backend = create_task_backend(name="memory")  # plan with backend_ref → memory

        # Assert — each plan gets the correct backend
        assert isinstance(local_backend, LocalYamlTaskProvider)
        assert isinstance(memory_backend, InMemoryTaskProvider)
        assert local_backend is not memory_backend
