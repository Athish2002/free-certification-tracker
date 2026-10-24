"""
CertPulse Visual Perceptual Hashing & Badge Registry Engine (Tier 3).

Implements:
1. PerceptualHashEngine: Native PIL + SciPy 2D Discrete Cosine Transform (DCT)
   difference hash (dHash) and perceptual hash (pHash) with zero external C-dependencies.
2. BadgeRegistry: Curated vendor emblem & certification badge catalog
   (Microsoft, AWS, Google Cloud, Oracle, Cisco, Kubernetes CKA/CKAD)
   with Hamming distance matching and similarity scoring.
"""

from __future__ import annotations

import io
import json
import logging
import os
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image, UnidentifiedImageError
from scipy.fftpack import dct
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("certpulse.visual_hasher")


class VisualHashError(Exception):
    """Custom exception raised for invalid image inputs or hash failures."""
    pass


# ==============================================================================
# 1. Pydantic Models for Badge Records and Verification Verdicts
# ==============================================================================

class BadgeRecord(BaseModel):
    """Catalog entry for an official vendor emblem or certification badge."""
    model_config = ConfigDict(extra="ignore")

    badge_id: str = Field(..., description="Unique badge slug (e.g. 'microsoft_certified')")
    provider: str = Field(..., description="Vendor/Platform name (e.g. 'Microsoft Azure')")
    badge_title: str = Field(..., description="Official title of the credential/emblem")
    dhash: str = Field(..., min_length=16, max_length=16, description="16-hex character difference hash")
    phash: str = Field(..., min_length=16, max_length=16, description="16-hex character perceptual hash")
    category: str = Field(default="proctored_exam", description="'proctored_exam' or 'skill_badge'")
    max_tolerance: int = Field(default=10, ge=0, le=64, description="Max Hamming distance threshold for authentic match")
    aliases: List[str] = Field(default_factory=list, description="Associated search aliases / keywords")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional provenance metadata")
    hash_captured_at: Optional[str] = Field(default=None, description="ISO-8601 UTC timestamp of hash capture")
    recommended_refresh_after: Optional[str] = Field(default=None, description="ISO-8601 UTC timestamp when hash should be refreshed")


class BadgeMatchResult(BaseModel):
    """Result of querying target visual hashes against registered badges."""
    model_config = ConfigDict(extra="ignore")

    matched: bool = Field(..., description="True if target hash matches a registered badge within tolerance")
    badge: Optional[BadgeRecord] = Field(default=None, description="Matched badge record if found")
    distance_phash: int = Field(default=64, ge=0, le=64, description="Hamming distance for pHash")
    distance_dhash: int = Field(default=64, ge=0, le=64, description="Hamming distance for dHash")
    min_distance: int = Field(default=64, ge=0, le=64, description="Minimum distance across evaluated hashes")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized similarity score (0.0 to 1.0)")
    hash_type_matched: str = Field(default="none", description="'phash' | 'dhash' | 'both' | 'none'")
    verdict_notes: str = Field(default="", description="Human-readable explanation of matching verdict")


# ==============================================================================
# 2. Perceptual Hash Engine (PIL + NumPy + SciPy DCT)
# ==============================================================================

class PerceptualHashEngine:
    """
    Computes difference hash (dHash) and 2D DCT perceptual hash (pHash)
    using only installed PIL, NumPy, and SciPy libraries (no OpenCV or imagehash required).
    """

    @staticmethod
    def _open_image(image_input: Union[str, Path, bytes, BinaryIO, Image.Image]) -> Image.Image:
        """
        Safely loads an image into a PIL Image instance.
        Validates non-empty input and traps corrupt data.
        """
        if image_input is None:
            raise VisualHashError("Image input cannot be None")

        if isinstance(image_input, Image.Image):
            return image_input.copy()

        if isinstance(image_input, (str, Path)):
            path = Path(image_input)
            if not path.exists():
                raise FileNotFoundError(f"Image file does not exist: {path}")
            if path.stat().st_size == 0:
                raise VisualHashError(f"Image file is empty (0 bytes): {path}")
            try:
                with Image.open(path) as img:
                    return img.convert("RGB")
            except Image.DecompressionBombError as e:
                raise VisualHashError(f"Decompression bomb detected: {e}") from e
            except (UnidentifiedImageError, OSError) as e:
                raise VisualHashError(f"Cannot identify image file {path}: {e}") from e

        if isinstance(image_input, bytes):
            if len(image_input) == 0:
                raise VisualHashError("Image bytes payload is empty (0 bytes)")
            try:
                with Image.open(io.BytesIO(image_input)) as img:
                    return img.convert("RGB")
            except Image.DecompressionBombError as e:
                raise VisualHashError(f"Decompression bomb detected: {e}") from e
            except (UnidentifiedImageError, OSError) as e:
                raise VisualHashError(f"Cannot identify image from bytes: {e}") from e

        if hasattr(image_input, "read"):
            data = image_input.read()
            if not data:
                raise VisualHashError("Image stream is empty")
            try:
                with Image.open(io.BytesIO(data)) as img:
                    return img.convert("RGB")
            except Image.DecompressionBombError as e:
                raise VisualHashError(f"Decompression bomb detected: {e}") from e
            except (UnidentifiedImageError, OSError) as e:
                raise VisualHashError(f"Cannot identify image from stream: {e}") from e

        raise VisualHashError(f"Unsupported image input type: {type(image_input)}")

    @classmethod
    def compute_dhash(
        cls,
        image_input: Union[str, Path, bytes, BinaryIO, Image.Image],
        hash_size: int = 8,
    ) -> str:
        """
        Computes 64-bit difference hash (dHash) as a 16-hex-character string.

        Algorithm:
        1. Convert image to grayscale (mode 'L').
        2. Resize to (hash_size + 1, hash_size) using LANCZOS filter.
        3. Compute column-wise difference matrix: diff[y, x] = pixels[y, x+1] > pixels[y, x].
        4. Bit-pack the 64 booleans into an integer and return lowercase 16-hex string.
        """
        img = cls._open_image(image_input)
        try:
            gray = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            pixels = np.array(gray, dtype=np.int32)
            diff = pixels[:, 1:] > pixels[:, :-1]
            bits = diff.flatten()
            val = int("".join("1" if b else "0" for b in bits), 2)
            hex_str = f"{val:016x}"
            return hex_str
        finally:
            img.close()

    @classmethod
    def compute_phash(
        cls,
        image_input: Union[str, Path, bytes, BinaryIO, Image.Image],
        hash_size: int = 8,
        highfreq_factor: int = 4,
    ) -> str:
        """
        Computes 64-bit 2D Discrete Cosine Transform (DCT) perceptual hash (pHash).

        Algorithm:
        1. Convert image to grayscale (mode 'L').
        2. Resize to (img_size, img_size) where img_size = hash_size * highfreq_factor (32x32).
        3. Check for 0-variance (flat solid images); return "0"*16 if uniform.
        4. Compute 2D DCT using scipy.fftpack.dct with orthogonal normalization.
        5. Extract top-left low-frequency submatrix (hash_size x hash_size).
        6. Compute median value of low frequencies.
        7. Threshold matrix: diff = dct_low > median.
        8. Bit-pack into 64-bit integer and return lowercase 16-hex string.
        """
        img = cls._open_image(image_input)
        try:
            img_size = hash_size * highfreq_factor
            gray = img.convert("L").resize((img_size, img_size), Image.Resampling.LANCZOS)
            pixels = np.array(gray, dtype=np.float64)

            # Flat uniform image guard (guarantees solid black and white yield distance 0)
            if np.ptp(pixels) == 0.0:
                return "0" * (hash_size * hash_size // 4)

            # 2D DCT with ortho normalization
            dct_rows = dct(pixels, axis=0, norm="ortho")
            dct_mat = dct(dct_rows, axis=1, norm="ortho")

            # Extract low frequencies
            dct_low = dct_mat[:hash_size, :hash_size]
            med = float(np.median(dct_low))
            diff = dct_low > med
            bits = diff.flatten()
            val = int("".join("1" if b else "0" for b in bits), 2)
            hex_str = f"{val:016x}"
            return hex_str
        finally:
            img.close()

    @classmethod
    def compute_hashes(
        cls,
        image_input: Union[str, Path, bytes, BinaryIO, Image.Image],
        hash_size: int = 8,
    ) -> Tuple[str, str]:
        """Computes both dHash and pHash in one invocation, returning (dhash, phash)."""
        dhash = cls.compute_dhash(image_input, hash_size=hash_size)
        phash = cls.compute_phash(image_input, hash_size=hash_size)
        return dhash, phash

    @staticmethod
    def hamming_distance(hash1: Union[str, int], hash2: Union[str, int]) -> int:
        """
        Computes the bitwise Hamming distance (count of differing bits) between two hashes.
        Accepts 16-hex strings or 64-bit integers.
        """
        if isinstance(hash1, str):
            h1_clean = hash1.strip().lower()
            if not h1_clean or len(h1_clean) != 16 or any(c not in "0123456789abcdef" for c in h1_clean):
                raise ValueError(f"hash1 must be a valid 16-hex-character string, got: '{hash1}'")
            val1 = int(h1_clean, 16)
        elif isinstance(hash1, int):
            val1 = hash1
        else:
            raise TypeError(f"hash1 must be str or int, got {type(hash1)}")

        if isinstance(hash2, str):
            h2_clean = hash2.strip().lower()
            if not h2_clean or len(h2_clean) != 16 or any(c not in "0123456789abcdef" for c in h2_clean):
                raise ValueError(f"hash2 must be a valid 16-hex-character string, got: '{hash2}'")
            val2 = int(h2_clean, 16)
        elif isinstance(hash2, int):
            val2 = hash2
        else:
            raise TypeError(f"hash2 must be str or int, got {type(hash2)}")

        # XOR bit count via native Python int.bit_count()
        xor_val = val1 ^ val2
        return xor_val.bit_count()

    @classmethod
    def similarity(cls, hash1: Union[str, int], hash2: Union[str, int], total_bits: int = 64) -> float:
        """Returns a normalized similarity score between 0.0 and 1.0 (1.0 = identical)."""
        dist = cls.hamming_distance(hash1, hash2)
        return max(0.0, min(1.0, 1.0 - (dist / total_bits)))

    @classmethod
    def is_match(cls, hash1: Union[str, int], hash2: Union[str, int], max_distance: int = 10) -> bool:
        """Returns True if Hamming distance between two hashes is within max_distance."""
        return cls.hamming_distance(hash1, hash2) <= max_distance


# ==============================================================================
# 3. Canonical Vendor Reference Badges Database
# ==============================================================================

DEFAULT_REFERENCE_BADGES: Dict[str, Dict[str, Any]] = {
    # 1. Microsoft Certified
    "microsoft_certified_voucher": {
        "badge_id": "microsoft_certified_voucher",
        "provider": "Microsoft Azure",
        "badge_title": "Microsoft Azure Certification Voucher Portal Header",
        "dhash": "436eb07179b9c061",
        "phash": "ca27254a2f25dab9",
        "category": "proctored_exam",
        "max_tolerance": 10,
        "aliases": ["microsoft", "azure", "msft", "az-900", "voucher"],
        "metadata": {"source_screenshot": "microsoft-azure-free-microsoft-exam-voucher-wave.png"},
    },
    "microsoft_azure_retake": {
        "badge_id": "microsoft_azure_retake",
        "provider": "Microsoft Azure",
        "badge_title": "Microsoft Learn Exam Discount & Retake Portal",
        "dhash": "cdcd6be3c50d17a4",
        "phash": "aa8b91b2e4993ec6",
        "category": "proctored_exam",
        "max_tolerance": 10,
        "aliases": ["microsoft", "azure", "retake", "exam_discount"],
        "metadata": {"source_screenshot": "microsoft-azure-azure-50-off-free-retake.png"},
    },

    # 2. Amazon Web Services (AWS) Certified
    "aws_certified_official": {
        "badge_id": "aws_certified_official",
        "provider": "Amazon Web Services",
        "badge_title": "AWS Certified Official Voucher & Exam Portal",
        "dhash": "9c80477b77207c48",
        "phash": "9f52501f1f3c602f",
        "category": "proctored_exam",
        "max_tolerance": 10,
        "aliases": ["aws", "amazon", "aws_certified", "cloud_practitioner", "solutions_architect"],
        "metadata": {"source_screenshot": "aws-50-discount-voucher.png"},
    },
    "aws_educate_badge": {
        "badge_id": "aws_educate_badge",
        "provider": "Amazon Web Services",
        "badge_title": "AWS Educate Official Training Emblem",
        "dhash": "9880677478236567",
        "phash": "ce936459376c2927",
        "category": "skill_badge",
        "max_tolerance": 10,
        "aliases": ["aws", "educate", "student_badge"],
        "metadata": {"source_screenshot": "aws-educate-badges.png"},
    },

    # 3. Google Cloud Certified
    "google_cloud_certified": {
        "badge_id": "google_cloud_certified",
        "provider": "Google Cloud",
        "badge_title": "Google Cloud Associate Cloud Engineer Official Challenge",
        "dhash": "528d2cb19b645c4c",
        "phash": "97e017cda99c1e70",
        "category": "proctored_exam",
        "max_tolerance": 10,
        "aliases": ["gcp", "google", "google_cloud", "ace", "pca"],
        "metadata": {"source_screenshot": "hist-gcp-ace-challenge.png"},
    },
    "gcp_cloud_skills_boost": {
        "badge_id": "gcp_cloud_skills_boost",
        "provider": "Google Cloud",
        "badge_title": "Google Cloud Skills Boost Arcade Official Header",
        "dhash": "9bd0e8ce15084916",
        "phash": "c285bdda3d82299b",
        "category": "skill_badge",
        "max_tolerance": 10,
        "aliases": ["gcp", "skills_boost", "arcade"],
        "metadata": {"source_screenshot": "gcp-cloud-skills-boost.png"},
    },

    # 4. Oracle Certified
    "oracle_mylearn_certified": {
        "badge_id": "oracle_mylearn_certified",
        "provider": "Oracle Cloud",
        "badge_title": "Oracle University MyLearn OCI Certification Portal Header",
        "dhash": "000810080c000000",
        "phash": "e63319cce6b3194c",
        "category": "proctored_exam",
        "max_tolerance": 10,
        "aliases": ["oracle", "oci", "mylearn", "oracle_certified"],
        "metadata": {"source_screenshot": "oracle-oci-free-cert.png"},
    },
    "oracle_oci_genai": {
        "badge_id": "oracle_oci_genai",
        "provider": "Oracle Cloud",
        "badge_title": "Oracle Cloud Infrastructure Generative AI Certification Portal",
        "dhash": "000810080c000000",
        "phash": "b3664c99b3e64c19",
        "category": "proctored_exam",
        "max_tolerance": 10,
        "aliases": ["oracle", "oci", "genai", "ai_cert"],
        "metadata": {"source_screenshot": "oracle-oci-generative-ai-cert.png"},
    },

    # 5. Cisco Certified
    "cisco_netacad_cyberops": {
        "badge_id": "cisco_netacad_cyberops",
        "provider": "Cisco",
        "badge_title": "Cisco Networking Academy CyberOps Official Portal",
        "dhash": "d861633771714c49",
        "phash": "ea6c959391b54d4a",
        "category": "proctored_exam",
        "max_tolerance": 10,
        "aliases": ["cisco", "netacad", "cyberops", "ccna"],
        "metadata": {"source_screenshot": "cisco-netacad-cyberops.png"},
    },
    "cisco_rev_up_recert": {
        "badge_id": "cisco_rev_up_recert",
        "provider": "Cisco",
        "badge_title": "Cisco Rev Up to Recert Official CE Portal",
        "dhash": "01898eb8f000b979",
        "phash": "9261eaca9512e5ee",
        "category": "proctored_exam",
        "max_tolerance": 10,
        "aliases": ["cisco", "rev_up", "recert", "continuing_education"],
        "metadata": {"source_screenshot": "cisco-rev-up-recert.png"},
    },

    # 6. Kubernetes CKA/CKAD (Linux Foundation / CNCF)
    "kubernetes_cka_ckad": {
        "badge_id": "kubernetes_cka_ckad",
        "provider": "Linux Foundation / CNCF",
        "badge_title": "CNCF Dan Kohn Kubernetes Scholarship Official Emblem",
        "dhash": "5529b6962e661e0e",
        "phash": "f44e4b5232794c4f",
        "category": "proctored_exam",
        "max_tolerance": 10,
        "aliases": ["kubernetes", "cncf", "cka", "ckad", "linux_foundation"],
        "metadata": {"source_screenshot": "cncf-dan-kohn-scholarship.png"},
    },
    "linux_foundation_lift": {
        "badge_id": "linux_foundation_lift",
        "provider": "Linux Foundation / CNCF",
        "badge_title": "Linux Foundation LiFT Annual Scholarship Portal",
        "dhash": "333300200065590e",
        "phash": "dd4ca8ae4407a6f3",
        "category": "proctored_exam",
        "max_tolerance": 10,
        "aliases": ["linux_foundation", "lift", "scholarship"],
        "metadata": {"source_screenshot": "linux-foundation-lift.png"},
    },
}

for _badge_entry in DEFAULT_REFERENCE_BADGES.values():
    _badge_entry.setdefault("hash_captured_at", "2026-01-01T00:00:00Z")
    _badge_entry.setdefault("recommended_refresh_after", "2026-12-31T23:59:59Z")


# ==============================================================================
# 4. Badge Registry Implementation
# ==============================================================================

class BadgeRegistry:
    """
    Catalog and matching engine for authentic vendor emblems and certification badges.
    Supports in-memory storage, JSON disk persistence, and fuzzy Hamming distance lookup.
    """

    def __init__(self, storage_path: Optional[Union[str, Path]] = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else None
        self._badges: Dict[str, BadgeRecord] = {}
        self._load_defaults()
        if self.storage_path and self.storage_path.exists():
            self.load_from_json(self.storage_path)
        else:
            # Check if default data/reference_badges.json exists
            default_json = Path(__file__).resolve().parent.parent / "data" / "reference_badges.json"
            if default_json.exists():
                try:
                    self.load_from_json(default_json)
                except Exception as e:
                    logger.debug(f"Could not load reference_badges.json: {e}")

    def _load_defaults(self) -> None:
        """Populates registry with canonical vendor reference badges."""
        for badge_data in DEFAULT_REFERENCE_BADGES.values():
            badge = BadgeRecord(**badge_data)
            self._badges[badge.badge_id] = badge

    def register_badge(self, badge: Union[BadgeRecord, Dict[str, Any]]) -> BadgeRecord:
        """Registers or updates a badge record in the catalog."""
        if isinstance(badge, dict):
            badge = BadgeRecord(**badge)
        self._badges[badge.badge_id] = badge
        return badge

    def get_badge(self, badge_id: str) -> Optional[BadgeRecord]:
        """Retrieves a badge by its unique slug."""
        return self._badges.get(badge_id)

    def list_badges(self, provider: Optional[str] = None) -> List[BadgeRecord]:
        """Lists all registered badges, optionally filtered by provider."""
        if provider:
            p_clean = provider.strip().lower()
            return [b for b in self._badges.values() if p_clean in b.provider.lower()]
        return list(self._badges.values())

    def list_vendors(self) -> List[str]:
        """Returns unique sorted list of recognized providers."""
        return sorted(list({b.provider for b in self._badges.values()}))

    def check_badge_freshness(self, badge: BadgeRecord) -> bool:
        """
        Checks if badge hash has exceeded its recommended_refresh_after timestamp.
        Returns True if fresh (or no expiry set), False if stale. Emits [BADGE HASH STALE] warning if stale.
        """
        if not badge.recommended_refresh_after:
            return True
        try:
            from datetime import datetime, timezone
            dt_str = badge.recommended_refresh_after.replace("Z", "+00:00")
            expiry = datetime.fromisoformat(dt_str)
            now = datetime.now(timezone.utc)
            if now > expiry:
                logger.warning(
                    f"[BADGE HASH STALE] Reference badge '{badge.badge_id}' ({badge.badge_title}) "
                    f"exceeded recommended refresh date ({badge.recommended_refresh_after}). Re-harvest from vendor CDN recommended."
                )
                return False
        except Exception as e:
            logger.debug(f"Error checking freshness for badge '{badge.badge_id}': {e}")
        return True

    def get_stale_badges(self) -> List[BadgeRecord]:
        """Returns all registered badges whose hash has exceeded recommended_refresh_after."""
        return [b for b in self._badges.values() if not self.check_badge_freshness(b)]

    def find_match(
        self,
        target_hash: str,
        hash_type: str = "phash",
        max_distance: int = 10,
        provider_filter: Optional[str] = None,
    ) -> Optional[BadgeMatchResult]:
        """
        Finds the closest registered badge matching the target hash within max_distance.
        Returns BadgeMatchResult or None if no badge is within tolerance.
        """
        matches = self.match_all(
            target_hash=target_hash,
            hash_type=hash_type,
            max_distance=max_distance,
            provider_filter=provider_filter,
        )
        return matches[0] if matches else None

    def match_all(
        self,
        target_hash: str,
        hash_type: str = "phash",
        max_distance: int = 10,
        provider_filter: Optional[str] = None,
    ) -> List[BadgeMatchResult]:
        """
        Returns all registered badges within max_distance sorted by ascending Hamming distance.
        """
        results: List[BadgeMatchResult] = []
        candidates = self.list_badges(provider=provider_filter)

        for badge in candidates:
            ref_hash = badge.phash if hash_type == "phash" else badge.dhash
            tolerance = min(max_distance, badge.max_tolerance)

            try:
                dist = PerceptualHashEngine.hamming_distance(target_hash, ref_hash)
            except ValueError:
                continue

            if dist <= tolerance:
                self.check_badge_freshness(badge)
                conf = PerceptualHashEngine.similarity(target_hash, ref_hash)
                notes = (
                    f"Authentic {badge.provider} emblem verified: "
                    f"'{badge.badge_title}' (Hamming distance {dist}/{tolerance}, {conf*100:.1f}% confidence)"
                )
                results.append(
                    BadgeMatchResult(
                        matched=True,
                        badge=badge,
                        distance_phash=dist if hash_type == "phash" else 64,
                        distance_dhash=dist if hash_type == "dhash" else 64,
                        min_distance=dist,
                        confidence=conf,
                        hash_type_matched=hash_type,
                        verdict_notes=notes,
                    )
                )

        results.sort(key=lambda r: (r.min_distance, -r.confidence))
        return results

    def match_image(
        self,
        image_input: Union[str, Path, bytes, BinaryIO, Image.Image],
        max_distance: int = 10,
        provider_filter: Optional[str] = None,
    ) -> BadgeMatchResult:
        """
        Computes both dHash and pHash on the input image and evaluates against the badge registry.
        Prefers pHash matching, with dHash corroboration.
        """
        try:
            dhash, phash = PerceptualHashEngine.compute_hashes(image_input)
        except Exception as e:
            return BadgeMatchResult(
                matched=False,
                badge=None,
                distance_phash=64,
                distance_dhash=64,
                min_distance=64,
                confidence=0.0,
                hash_type_matched="none",
                verdict_notes=f"Visual hashing failed on input: {e}",
            )

        p_matches = self.match_all(phash, hash_type="phash", max_distance=max_distance, provider_filter=provider_filter)
        d_matches = self.match_all(dhash, hash_type="dhash", max_distance=max_distance, provider_filter=provider_filter)

        best_p = p_matches[0] if p_matches else None
        best_d = d_matches[0] if d_matches else None

        if best_p and best_d and best_p.badge and best_d.badge and best_p.badge.badge_id == best_d.badge.badge_id:
            return BadgeMatchResult(
                matched=True,
                badge=best_p.badge,
                distance_phash=best_p.min_distance,
                distance_dhash=best_d.min_distance,
                min_distance=min(best_p.min_distance, best_d.min_distance),
                confidence=max(best_p.confidence, best_d.confidence),
                hash_type_matched="both",
                verdict_notes=(
                    f"Strong dual-hash match for {best_p.badge.provider} ('{best_p.badge.badge_title}'): "
                    f"pHash dist={best_p.min_distance}, dHash dist={best_d.min_distance}"
                ),
            )

        if best_p:
            d_dist = PerceptualHashEngine.hamming_distance(dhash, best_p.badge.dhash) if best_p.badge else 64
            return BadgeMatchResult(
                matched=True,
                badge=best_p.badge,
                distance_phash=best_p.min_distance,
                distance_dhash=d_dist,
                min_distance=best_p.min_distance,
                confidence=best_p.confidence,
                hash_type_matched="phash",
                verdict_notes=best_p.verdict_notes,
            )

        if best_d:
            p_dist = PerceptualHashEngine.hamming_distance(phash, best_d.badge.phash) if best_d.badge else 64
            return BadgeMatchResult(
                matched=True,
                badge=best_d.badge,
                distance_phash=p_dist,
                distance_dhash=best_d.min_distance,
                min_distance=best_d.min_distance,
                confidence=best_d.confidence,
                hash_type_matched="dhash",
                verdict_notes=best_d.verdict_notes,
            )

        return BadgeMatchResult(
            matched=False,
            badge=None,
            distance_phash=64,
            distance_dhash=64,
            min_distance=64,
            confidence=0.0,
            hash_type_matched="none",
            verdict_notes=(
                f"No registered vendor emblem matched (pHash='{phash}', dHash='{dhash}'). "
                f"Hamming distance exceeded threshold tau={max_distance}."
            ),
        )

    def save_to_json(self, target_path: Optional[Union[str, Path]] = None) -> Path:
        """Serializes the badge catalog to a formatted JSON file."""
        dest = Path(target_path or self.storage_path or "data/reference_badges.json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        serialized = {badge_id: badge.model_dump() for badge_id, badge in self._badges.items()}
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2, ensure_ascii=False)
        return dest

    def load_from_json(self, source_path: Union[str, Path]) -> int:
        """Loads and merges badges from a JSON file into the registry."""
        src = Path(source_path)
        if not src.exists():
            raise FileNotFoundError(f"Badge catalog file not found: {src}")
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for badge_id, raw_record in data.items():
            if "badge_id" not in raw_record:
                raw_record["badge_id"] = badge_id
            self.register_badge(raw_record)
            count += 1
        return count


# ==============================================================================
# 5. Global Singleton Accessors & Convenience Functions
# ==============================================================================

_GLOBAL_REGISTRY: Optional[BadgeRegistry] = None

def get_badge_registry() -> BadgeRegistry:
    """Returns the process-wide singleton BadgeRegistry instance."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = BadgeRegistry()
    return _GLOBAL_REGISTRY


def compute_dhash(image_input: Union[str, Path, bytes, BinaryIO, Image.Image], hash_size: int = 8) -> str:
    """Convenience helper to compute 64-bit dHash string."""
    return PerceptualHashEngine.compute_dhash(image_input, hash_size=hash_size)


def compute_phash(image_input: Union[str, Path, bytes, BinaryIO, Image.Image], hash_size: int = 8) -> str:
    """Convenience helper to compute 64-bit pHash string."""
    return PerceptualHashEngine.compute_phash(image_input, hash_size=hash_size)


def hamming_distance(hash1: Union[str, int], hash2: Union[str, int]) -> int:
    """Convenience helper to compute bitwise Hamming distance."""
    return PerceptualHashEngine.hamming_distance(hash1, hash2)


def match_badge(
    image_input: Union[str, Path, bytes, BinaryIO, Image.Image],
    max_distance: int = 10,
    provider: Optional[str] = None,
) -> BadgeMatchResult:
    """Convenience helper to match an image against the global BadgeRegistry."""
    return get_badge_registry().match_image(image_input, max_distance=max_distance, provider_filter=provider)


def match_badge_phash(
    image_path: Optional[Union[str, Path]] = None,
    image_bytes: Optional[bytes] = None,
    platform: Optional[str] = None,
    max_distance: int = 10,
) -> bool:
    """
    Convenience helper to check if an image matches any registered vendor badge via pHash.
    Returns True if matched, False otherwise.
    """
    target = image_bytes if image_bytes else image_path
    if not target:
        return False
    try:
        res = match_badge(target, max_distance=max_distance, provider=platform)
        return res.matched
    except Exception:
        return False


def should_skip_screenshot_write(
    new_image: Union[str, Path, bytes, BinaryIO, Image.Image],
    existing_screenshot_path: Union[str, Path],
    old_status: str,
    new_status: str,
    delta_threshold: float = 0.05,
) -> Tuple[bool, float, int]:
    """
    Evaluates whether writing a new screenshot to disk should be skipped via perceptual hash diffing.

    Returns:
        (should_skip: bool, delta: float, hamming_distance: int)

    Invariants:
        1. existing_screenshot_path must exist, be a regular file, have size >= 4096 bytes,
           and have valid PNG magic bytes b"\\x89PNG\\r\\n\\x1a\\n". If not, returns (False, 1.0, 64).
        2. If old_status != new_status: status has changed, so write cannot be skipped.
           Returns (False, 1.0, 64).
        3. Computes 64-bit DCT perceptual hash for new_image and existing_screenshot_path.
        4. Calculates bitwise Hamming distance and normalized delta = hamming_dist / 64.0.
        5. If delta < delta_threshold (i.e. hamming_dist <= 3 bits difference when delta_threshold=0.05),
           returns (True, delta, hamming_dist) to skip redundant disk writes.
        6. Otherwise returns (False, delta, hamming_dist).
    """
    # 1. Validate existing target screenshot file on disk
    if existing_screenshot_path is None:
        return False, 1.0, 64

    target = Path(existing_screenshot_path)
    if not target.exists() or not target.is_file():
        return False, 1.0, 64

    try:
        st = target.stat()
        if st.st_size < 4096:
            return False, 1.0, 64
        with open(target, "rb") as f:
            header = f.read(8)
        if header != b"\x89PNG\r\n\x1a\n":
            return False, 1.0, 64
    except Exception:
        return False, 1.0, 64

    # 2. Status change invariant: any status transition forces screenshot refresh
    if str(old_status).strip().lower() != str(new_status).strip().lower():
        return False, 1.0, 64

    # 3. Compute 64-bit DCT perceptual hashes and Hamming distance
    try:
        phash_new = PerceptualHashEngine.compute_phash(new_image)
        phash_existing = PerceptualHashEngine.compute_phash(target)
        dist = PerceptualHashEngine.hamming_distance(phash_new, phash_existing)
        delta = dist / 64.0
    except Exception as e:
        logger.warning("Perceptual hash computation failed during delta comparison: %s", e)
        return False, 1.0, 64

    # 4. Threshold check: skip write only if delta is strictly below threshold
    should_skip = delta < delta_threshold
    return should_skip, delta, dist

