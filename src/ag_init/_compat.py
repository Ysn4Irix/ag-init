"""Compatibility shims for Python 3.14+ and Rich unicode tables."""

from __future__ import annotations

import importlib
import os
import sys


def patch_rich_unicode() -> None:
    """Ensure Rich doesn't crash on Python 3.14+ (Unicode 17.0.0+).

    Python 3.14+ bundles Unicode 17.0.0+ (unicodedata.unidata_version == '17.0.0'),
    while Rich (up to v15.x) only includes unicode tables up to Unicode 16.0.0.
    Rich's dynamic loader constructs f"rich._unicode_data.unicode{version}",
    raising ModuleNotFoundError on Python 3.14+.
    """
    # 1. Enforce UNICODE_VERSION env var fallback if not already set
    if "UNICODE_VERSION" not in os.environ:
        os.environ["UNICODE_VERSION"] = "16.0.0"

    # 2. Defensive monkey-patch on rich._unicode_data.load if rich is installed/imported
    try:
        import rich._unicode_data

        orig_load = rich._unicode_data.load

        def safe_load(version: str | None = None):
            # Try original load first with explicit version or UNICODE_VERSION env var
            req_version = version or os.environ.get("UNICODE_VERSION", "16.0.0")
            try:
                return orig_load(req_version)
            except (ModuleNotFoundError, ImportError, Exception):
                # Fallback to the latest available table in rich._unicode_data
                for candidate in (
                    "unicode16-0-0",
                    "unicode15-1-0",
                    "unicode15-0-0",
                    "unicode14-0-0",
                ):
                    try:
                        return importlib.import_module(f"rich._unicode_data.{candidate}")
                    except (ModuleNotFoundError, ImportError):
                        continue
                raise

        rich._unicode_data.load = safe_load
    except Exception:
        pass


# Apply immediately upon import of _compat
patch_rich_unicode()
