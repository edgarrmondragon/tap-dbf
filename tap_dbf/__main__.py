"""Entrypoint module, in case you use `python -m tap_dbf`."""

from __future__ import annotations

from tap_dbf.tap import TapDBF

TapDBF.cli()
