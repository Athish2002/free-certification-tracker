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
from typing import Any, Dict, Optional, Union

import jsonschema

logger = logging.getLogger("certpulse.io_utils")


def load_schema(schema_path: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Loads JSON Schema from a file path or returns dictionary directly.
    Resolves relative paths against the project root / data directory if needed.
    """
    if isinstance(schema_path, dict):
        return schema_path

    path = Path(schema_path)
    if not path.is_absolute():
        # Try resolving relative to current working directory
        if not path.exists():
            # Try resolving relative to project root or data directory
            root_dir = Path(__file__).resolve().parent.parent
            if (root_dir / path).exists():
                path = root_dir / path
            elif (root_dir / "data" / path).exists():
                path = root_dir / "data" / path

    if not path.exists():
        raise FileNotFoundError(f"Schema file not found at: {schema_path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_payload(data: Any, schema_path: Union[str, Path, Dict[str, Any]]) -> None:
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
    target_path: Union[str, Path],
    data: Any,
    schema_path: Optional[Union[str, Path, Dict[str, Any]]] = None,
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
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        dir=str(target.parent),
        prefix=f".{target.name}.",
        suffix=".tmp",
        encoding="utf-8",
    )
    temp_path = Path(temp_file.name)

    try:
        json.dump(data, temp_file, indent=indent, ensure_ascii=ensure_ascii)
        temp_file.write("\n")
        temp_file.flush()
        temp_file.close()  # Must close file handle before os.replace on Windows!

        os.replace(temp_path, target)
        logger.debug("Atomically wrote %s via %s", target.name, temp_path.name)
    except Exception as exc:
        if not temp_file.closed:
            try:
                temp_file.close()
            except Exception:
                pass
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        logger.error("Atomic write failed for %s: %s", target, str(exc))
        raise exc


def read_json(path: Union[str, Path]) -> Any:
    """Reads JSON payload from path with UTF-8 encoding."""
    target = Path(path).resolve()
    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)
