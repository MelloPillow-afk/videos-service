# fmt: off
"""Generated collection for module-named files, with overridable plugin fixtures."""

from fnmatch import fnmatch
from pathlib import Path

import pytest

from . import _support


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "integration: exercises the service's real application"
    )
    config.addinivalue_line(
        "markers", "api_case(data): generated HTTP request and expectations"
    )
    if not config.pluginmanager.is_registered(_support):
        config.pluginmanager.register(_support, "ag-generated-tests")


def pytest_collect_file(
    file_path: Path, parent: pytest.Collector
) -> pytest.Module | None:
    if (
        file_path.parent != Path(__file__).parent
        or file_path.stem not in _support.MODULES
    ):
        return None
    # Let pytest collect conventional test_*.py names once through its normal hook.
    patterns = parent.config.getini("python_files")
    if any(
        fnmatch(file_path.name, pattern) or fnmatch(str(file_path), pattern)
        for pattern in patterns
    ):
        return None
    return pytest.Module.from_parent(parent, path=file_path)  # pyright: ignore[reportUnknownMemberType]
