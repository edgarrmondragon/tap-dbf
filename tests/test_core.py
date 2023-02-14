"""Test tap-dbf."""

from __future__ import annotations

from singer_sdk.testing import get_tap_test_class

from tap_dbf.tap import TapDBF

SAMPLE_CONFIG = {
    "path": "/files/*.dbf",
    "fs_root": "file://tests/data",
    "ignore_missing_memofile": True,
}

TestTapDBF = get_tap_test_class(TapDBF, config=SAMPLE_CONFIG)
