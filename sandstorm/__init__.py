"""Sandstorm Secure: local Android phone-management (MDM) core and CLI."""

from importlib.metadata import PackageNotFoundError, version
import pathlib
import tomllib


def get_version() -> str:
    """Return the package version from pyproject.toml (single source of truth)."""
    pyproject_path = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    if pyproject_path.is_file():
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        return str(data["project"]["version"])
    try:
        return version("sandstorm")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = get_version()
