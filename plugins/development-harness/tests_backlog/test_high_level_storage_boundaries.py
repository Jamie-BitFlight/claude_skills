from __future__ import annotations

import ast
from pathlib import Path
from types import ModuleType

import backlog_core.gh_client as gh_client
import backlog_core.operations as operations
import backlog_core.server as server
import sam_schema.server as sam_server


def _source(module: ModuleType) -> str:
    module_path = module.__file__
    assert module_path is not None
    return Path(module_path).read_text(encoding="utf-8")


def _imports(module: ModuleType) -> set[str]:
    source = _source(module)
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            prefix = "backlog_core." if node.level and module.__package__ == "backlog_core" else ""
            names.add(f"{prefix}{node.module}")
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def _attributes_by_function(module: ModuleType) -> dict[str, set[str]]:
    tree = ast.parse(_source(module))
    return {
        node.name: {child.attr for child in ast.walk(node) if isinstance(child, ast.Attribute)}
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_operations_has_no_high_level_storage_bypass() -> None:
    source = _source(operations)
    tree = ast.parse(source)
    called = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    forbidden_references = {"parse_backlog", "load_item", "save_item", "get_backlog_dir", "file_path"}
    assert not forbidden_references & (called | attributes)
    allowed_non_backlog_io = {"_resolve_groomed_content"}
    for function_name, function_attributes in _attributes_by_function(operations).items():
        if function_name not in allowed_non_backlog_io:
            assert not {"read_text", "write_text", "glob", "mkdir", "exists"} & function_attributes
    assert not _imports(operations) & {
        "backlog_core.yaml_io",
        "backlog_core.reconciliation",
        "backlog_core.artifact_provider",
    }


def test_github_client_has_no_cache_filesystem_access() -> None:
    source = _source(gh_client)
    tree = ast.parse(source)
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not {"get_backlog_dir", "state_root", "read_text", "write_text", "glob", "mkdir", "exists"} & attributes
    assert "dh_paths" not in _imports(gh_client)


def test_server_has_no_artifact_provider_or_filesystem_fallback() -> None:
    assert not _imports(server) & {"backlog_core.artifact_provider", "backlog_core.artifact_provider_local"}
    source = _source(server)
    assert "LocalFilesystemArtifactProvider" not in source
    assert "create_artifact_provider" not in source
    assert "artifact_migrate" not in source
    assert "_ds.read_dispatch_plan" not in source


def test_sam_server_has_no_task_backend_routing() -> None:
    assert "sam_schema.core.task_config" not in _imports(sam_server)
    source = _source(sam_server)
    assert "create_task_backend" not in source
    assert "task_file_path" not in source
