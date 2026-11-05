"""
CertPulse Atomic I/O and JSON Schema Pre-Flight Validation Module.

Provides safe, transactional JSON writes with pre-flight schema validation,
ensuring zero file corruption, atomic file replacement across POSIX and Windows,
and clean cleanup of temporary files on failures.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import jsonschema

logger = logging.getLogger("certpulse.io_utils")


def load_schema(schema_path: str | Path | dict[str, Any]) -> dict[str, Any]:
    """
    Loads JSON Schema from a file path or returns dictionary directly.
    Resolves relative paths against the project root / data directory if needed.
    """
    if isinstance(schema_path, dict):
        return schema_path

    path = Path(schema_path)
    if not path.is_absolute() and not path.exists():
        # Try resolving relative to project root or data directory
        root_dir = Path(__file__).resolve().parent.parent
        if (root_dir / path).exists():
            path = root_dir / path
        elif (root_dir / "data" / path).exists():
            path = root_dir / "data" / path

    if not path.exists():
        raise FileNotFoundError(f"Schema file not found at: {schema_path}")

    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_payload(data: Any, schema_path: str | Path | dict[str, Any]) -> None:
    """
    Validates data payload against the specified JSON Schema using jsonschema.validate.
    Raises jsonschema.ValidationError or jsonschema.SchemaError on failure with context.
    """
    schema = load_schema(schema_path)
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        logger.error("Pre-flight schema validation failed: %s (path: %s)", exc.message, exc.path)
        raise exc


def atomic_write_json(
    target_path: str | Path,
    data: Any,
    schema_path: str | Path | dict[str, Any] | None = None,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> None:
    """
    Atomically writes JSON payload to target_path using NamedTemporaryFile and os.replace.

    Pre-flight validation: If schema_path is provided, strictly validates data against
    the JSON schema prior to creating or modifying any file on disk.

    Windows-safe replacement: Ensures temporary file handle is explicitly flushed and closed
    before invoking os.replace to prevent WinError 32 file-lock collisions.
    Cleans up temporary file if any exception occurs before successful replacement.
    """
    target = Path(target_path).resolve()

    # Pre-flight validation prior to any disk I/O operations
    if schema_path is not None:
        validate_payload(data, schema_path)

    target.parent.mkdir(parents=True, exist_ok=True)

    # Create temporary file in same directory to guarantee same filesystem volume for atomic rename
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            dir=str(target.parent),
            prefix=f".{target.name}.",
            suffix=".tmp",
            encoding="utf-8",
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(data, temp_file, indent=indent, ensure_ascii=ensure_ascii)
            temp_file.write("\n")
            temp_file.flush()

        os.replace(temp_path, target)
        logger.debug("Atomically wrote %s via %s", target.name, temp_path.name)
    except Exception as exc:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError as unlink_err:
                logger.debug("Failed unlinking temp file %s: %s", temp_path, unlink_err)
        logger.error("Atomic write failed for %s: %s", target, str(exc))
        raise exc


def read_json(path: str | Path) -> Any:
    """Reads JSON payload from path with UTF-8 encoding."""
    target = Path(path).resolve()
    with open(target, encoding="utf-8") as f:
        return json.load(f)
