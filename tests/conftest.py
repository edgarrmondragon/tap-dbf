"""Pytest configuration for the tap-dbf tests."""
from __future__ import annotations

# register the singer_sdk pytest plugin
pytest_plugins = ("singer_sdk.testing.pytest_plugin",)
