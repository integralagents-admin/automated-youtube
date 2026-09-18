#!/usr/bin/env python3
"""Load the bundle's config.yaml and resolve every key.

Used by every component skill in the automated-youtube bundle so Drive IDs,
spreadsheet IDs, and folder names are never hard-coded.

Version: 0.2.0

Usage from a skill:

    from load_config import cfg
    sheet_id = cfg("posting_schedule.spreadsheet_id")
    root = cfg("drive.queues_root_folder_id")
    shortform_folder = cfg("drive.shortform_root_folder_name")

Override at runtime with an environment variable:

    AUTOYT__DRIVE__QUEUES_ROOT_FOLDER_ID=abc... python load_config.py drive.queues_root_folder_id
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - skill should not crash if PyYAML missing
    yaml = None


BUNDLE_ROOT = Path(os.environ.get("AUTOYT_BUNDLE_ROOT")
                   or Path(__file__).resolve().parent.parent)
CONFIG_PATH = BUNDLE_ROOT / "config.yaml"


def _flatten(prefix: str, value: Any, out: dict[str, str]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(f"{prefix}.{k}" if prefix else k, v, out)
    else:
        out[prefix] = "" if value is None else str(value)


def _load_yaml() -> dict[str, str]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"bundle config not found at {CONFIG_PATH}. "
            "Run from the automated-youtube bundle or set AUTOYT_BUNDLE_ROOT."
        )
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required to read config.yaml. Install with `pip install pyyaml`."
        )
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    flat: dict[str, str] = {}
    _flatten("", raw, flat)
    return flat


def _override_key(dotted: str) -> str:
    return "AUTOYT__" + dotted.upper().replace(".", "__")


def cfg(dotted_key: str, default: str | None = None, required: bool = False) -> str:
    """Return a config value by dotted key.

    Precedence: AUTOYT__<SECTION>__<KEY> environment variable > config.yaml > default.

    Values are run through `os.path.expanduser` so that entries starting with
    `~` resolve against the running user's home. This keeps path-shaped config
    values usable from any caller without shell tilde expansion.
    """
    env_value = os.environ.get(_override_key(dotted_key))
    if env_value is not None:
        return os.path.expanduser(env_value)
    flat = _load_yaml()
    value = flat.get(dotted_key)
    if value is None or value == "":
        if required:
            raise KeyError(f"required config key {dotted_key!r} is missing")
        return default if default is not None else ""
    return os.path.expanduser(value)


def all_keys() -> list[str]:
    """List every dotted key defined in config.yaml (override env vars win)."""
    return sorted(_load_yaml().keys())


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: load_config.py <dotted.key> [<dotted.key> ...]")
        return 2
    rc = 0
    for key in argv[1:]:
        try:
            print(f"{key}={cfg(key, required=True)}")
        except (KeyError, FileNotFoundError, RuntimeError) as exc:
            print(f"{key}=ERROR: {exc}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))