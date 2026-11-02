"""Compatibility shims for Python 3.14+ and Rich unicode tables."""

from __future__ import annotations

import importlib
import os
import sys


def patch_rich_unicode() -> None:
    """Ensure Rich doesn't crash on Python 3.14+ (Unicode 17.0.0+) or when venv is uninstalled.

    Python 3.14+ bundles Unicode 17.0.0+ (unicodedata.unidata_version == '17.0.0'),
    while Rich (up to v15.x) only includes unicode tables up to Unicode 16.0.0.
    Rich's dynamic loader constructs f"rich._unicode_data.unicode{version}",
    raising ModuleNotFoundError on Python 3.14+.

    Additionally, eagerly preloading the unicode tables into memory ensures that
    operations like `ag-init uninstall` do not crash with ModuleNotFoundError
    when the package manager removes the virtualenv files from disk while Python is running.
    """
    # 1. Enforce UNICODE_VERSION env var fallback if not already set
    if "UNICODE_VERSION" not in os.environ:
        os.environ["UNICODE_VERSION"] = "16.0.0"

    # 2. Defensive monkey-patch on rich._unicode_data.load if rich is installed/imported
    try:
        import rich._unicode_data

        orig_load = rich._unicode_data.load
        _cached_table = None

        # Eagerly preload a fallback unicode table directly into memory
        for candidate in ("16-0-0", "15-1-0", "15-0-0", "14-0-0"):
            try:
                mod = importlib.import_module(f".unicode{candidate}", "rich._unicode_data")
                if hasattr(mod, "cell_table"):
                    _cached_table = mod.cell_table
                    break
            except Exception:
                continue

        def safe_load(unicode_version: str = "auto"):
            nonlocal _cached_table
            if _cached_table is not None and unicode_version in ("auto", "latest", None):
                return _cached_table

            req_version = unicode_version if unicode_version not in ("auto", "latest", None) else os.environ.get("UNICODE_VERSION", "16.0.0")
            try:
                table = orig_load(req_version)
                if unicode_version in ("auto", "latest", None):
                    _cached_table = table
                return table
            except (ModuleNotFoundError, ImportError, Exception):
                if _cached_table is not None:
                    return _cached_table
                for candidate in ("16-0-0", "15-1-0", "15-0-0", "14-0-0"):
                    try:
                        mod = importlib.import_module(f".unicode{candidate}", "rich._unicode_data")
                        if hasattr(mod, "cell_table"):
                            _cached_table = mod.cell_table
                            return _cached_table
                    except (ModuleNotFoundError, ImportError):
                        continue
                raise

        rich._unicode_data.load = safe_load

        # Eagerly preload and cache the table in memory during startup
        try:
            _cached_table = safe_load()
        except Exception:
            pass

    except Exception:
        pass

    # 3. Pre-import typer.rich_utils to prevent excepthook failure if venv is uninstalled
    try:
        import typer.rich_utils  # noqa: F401
    except Exception:
        pass



# Apply immediately upon import of _compat
patch_rich_unicode()
