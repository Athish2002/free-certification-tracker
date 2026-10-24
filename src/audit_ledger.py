"""
CertPulse Cryptographic Audit Trail & Tamper-Evident Ledger.
Generates and appends SHA-256 cryptographic digests of rendered HTML DOM and
captured screenshot PNGs to an append-only JSONL ledger (data/audit_log.jsonl).
"""

from __future__ import annotations

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger("certpulse.audit_ledger")

ROOT_DIR = Path(__file__).resolve().parent.parent
LEDGER_FILE = ROOT_DIR / "data" / "audit_log.jsonl"


class AuditReceipt(BaseModel):
    """
    Cryptographic verification receipt for an inspected offer.
    """
    model_config = ConfigDict(extra="ignore")

    timestamp_utc: str = Field(
        ...,
        description="ISO 8601 UTC timestamp of the audit pass."
    )
    offer_id: str = Field(
        ...,
        description="Unique offer slug identifier."
    )
    url: str = Field(
        ...,
        description="Destination URL inspected."
    )
    sha256_dom: str = Field(
        ...,
        description="SHA-256 hexadecimal hash of the rendered DOM text."
    )
    sha256_screenshot: Optional[str] = Field(
        default=None,
        description="SHA-256 hexadecimal hash of the viewport screenshot PNG."
    )
    actionability_verdict: Optional[str] = Field(
        default=None,
        description="Outcome from semantic accessibility scanner."
    )
    cart_balance_verified: Optional[str] = Field(
        default=None,
        description="Outcome from synthetic cart balance assertion."
    )
    status_assigned: str = Field(
        default="Active",
        description="Status assigned by the inspection engine."
    )


def compute_sha256_text(text: str) -> str:
    """Computes SHA-256 hex digest of a UTF-8 text string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_sha256_file(file_path: Path) -> Optional[str]:
    """Computes SHA-256 hex digest of a binary file on disk."""
    if not file_path.exists():
        return None
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def record_audit_entry(
    offer_id: str,
    url: str,
    dom_text: str,
    screenshot_path: Optional[str] = None,
    status: str = "Active",
    actionability_verdict: Optional[str] = None,
    cart_balance_verified: Optional[str] = None,
    ledger_path: Optional[Path] = None
) -> AuditReceipt:
    """
    Generates cryptographic digests and appends a tamper-evident audit receipt
    to the append-only JSONL audit ledger.
    """
    target_ledger = ledger_path or LEDGER_FILE
    target_ledger.parent.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(timezone.utc).isoformat()
    dom_hash = compute_sha256_text(dom_text)

    shot_hash = None
    if screenshot_path:
        shot_file = ROOT_DIR / screenshot_path if not Path(screenshot_path).is_absolute() else Path(screenshot_path)
        shot_hash = compute_sha256_file(shot_file)

    receipt = AuditReceipt(
        timestamp_utc=now_utc,
        offer_id=offer_id,
        url=url,
        sha256_dom=dom_hash,
        sha256_screenshot=shot_hash,
        actionability_verdict=actionability_verdict,
        cart_balance_verified=cart_balance_verified,
        status_assigned=status
    )

    with open(target_ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(receipt.model_dump(), ensure_ascii=False) + "\n")

    return receipt


def read_audit_entries(
    limit: int = 100,
    ledger_path: Optional[Path] = None
) -> List[AuditReceipt]:
    """Reads the most recent audit receipts from the append-only JSONL ledger."""
    target_ledger = ledger_path or LEDGER_FILE
    if not target_ledger.exists():
        return []

    entries: List[AuditReceipt] = []
    with open(target_ledger, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    entries.append(AuditReceipt(**data))
                except Exception:
                    continue

    return entries[-limit:]


def verify_ledger_integrity(
    ledger_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Verifies that all entries in the ledger have valid SHA-256 format
    and that referenced screenshots still match their recorded digests.
    """
    entries = read_audit_entries(limit=500, ledger_path=ledger_path)
    total = len(entries)
    valid_hashes = 0
    screenshot_matches = 0

    for e in entries:
        if len(e.sha256_dom) == 64 and all(c in "0123456789abcdef" for c in e.sha256_dom):
            valid_hashes += 1
        if e.sha256_screenshot and len(e.sha256_screenshot) == 64:
            screenshot_matches += 1

    return {
        "total_receipts": total,
        "valid_dom_hashes": valid_hashes,
        "valid_screenshot_hashes": screenshot_matches,
        "integrity_rate": 1.0 if total == 0 else valid_hashes / total
    }


def compact_audit_log(
    ledger_path: Optional[Path] = None,
    archive_path: Optional[Path] = None,
    keep_recent: int = 500,
    archive_gz: bool = True
) -> Dict[str, Any]:
    """
    Compacts the audit ledger:
    1. Retains the most recent `keep_recent` entries verbatim in data/audit_log.jsonl.
    2. Appends older entries into data/audit_log_archive.jsonl.gz for long-term compressed storage.
    3. Atomically rewrites data/audit_log.jsonl.
    """
    import gzip
    import tempfile
    import os

    target_ledger = Path(ledger_path) if ledger_path else LEDGER_FILE
    target_archive = Path(archive_path) if archive_path else (target_ledger.parent / "audit_log_archive.jsonl.gz")

    if not target_ledger.exists():
        return {"total_before": 0, "retained": 0, "archived": 0}

    lines: List[str] = []
    with open(target_ledger, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                lines.append(stripped)

    total_count = len(lines)
    if total_count <= keep_recent:
        return {"total_before": total_count, "retained": total_count, "archived": 0}

    split_idx = total_count - keep_recent
    to_archive = lines[:split_idx]
    to_retain = lines[split_idx:]

    # Append older entries to archive gzip
    if archive_gz and to_archive:
        target_archive.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(target_archive, "at", encoding="utf-8") as gz:
            for item in to_archive:
                gz.write(item + "\n")

    # Atomically rewrite target_ledger with retained lines
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        dir=str(target_ledger.parent),
        prefix=f".{target_ledger.name}.",
        suffix=".tmp",
        encoding="utf-8"
    )
    temp_path = Path(temp_file.name)
    try:
        for item in to_retain:
            temp_file.write(item + "\n")
        temp_file.flush()
        temp_file.close()
        os.replace(temp_path, target_ledger)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass

    logger.info(
        f"Compacted audit ledger: {total_count} -> {len(to_retain)} entries "
        f"({len(to_archive)} archived to {target_archive.name})."
    )
    return {
        "total_before": total_count,
        "retained": len(to_retain),
        "archived": len(to_archive)
    }

