"""
CertPulse 3-Tier Progressive OCR Engine.
Progressive execution priority:
1. Tier A (Primary): pytesseract wrapper (if pytesseract and tesseract executable exist).
2. Tier B (Secondary): easyocr wrapper (if easyocr/torch exist and weights are cached).
3. Tier C (Universal Fallback): Native PIL contrast heuristic + DOM SVG/Canvas text extraction.
"""

from __future__ import annotations

import concurrent.futures
import html
import io
import logging
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.vlm.models import (
    OCRMethod,
    OCRResult,
    OCRStatus,
    KEY_PHRASE_PATTERNS,
    PRICE_REGEX,
    VOUCHER_CODE_REGEX,
    VOUCHER_STOPWORDS,
)

logger = logging.getLogger("certpulse.vlm.ocr")


class ProgressiveOCREngine:
    """
    3-Tier Progressive OCR Engine for Viewport Screenshot & Ground-Truth Verification.

    Execution Priority:
    1. Tier A (Primary): pytesseract wrapper (if pytesseract and tesseract executable exist).
    2. Tier B (Secondary): easyocr wrapper (if easyocr/torch exist and weights are cached).
    3. Tier C (Universal Fallback): Native PIL contrast heuristic + DOM SVG/Canvas text extraction.
    """

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        timeout_seconds: float = 5.0,
        enable_easyocr_download: bool = False
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.enable_easyocr_download = enable_easyocr_download

        self._tesseract_available: Optional[bool] = None
        self._easyocr_available: Optional[bool] = None
        self._easyocr_reader: Any = None
        self._tesseract_cmd: Optional[str] = tesseract_cmd

    # -------------------------------------------------------------------------
    # Tier A: pytesseract Availability & Execution
    # -------------------------------------------------------------------------
    @property
    def is_tesseract_available(self) -> bool:
        if self._tesseract_available is None:
            self._tesseract_available = self._probe_tesseract()
        return self._tesseract_available

    def _probe_tesseract(self) -> bool:
        """Verifies both pytesseract Python package and tesseract executable presence."""
        try:
            import pytesseract

            cmd = self._tesseract_cmd or shutil.which("tesseract") or shutil.which("tesseract.exe")

            if not cmd:
                win_candidates = [
                    Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
                    Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
                    Path.home() / "AppData/Local/Programs/Tesseract-OCR/tesseract.exe"
                ]
                for cand in win_candidates:
                    if cand.is_file():
                        cmd = str(cand)
                        break

            if cmd:
                pytesseract.pytesseract.tesseract_cmd = cmd
                pytesseract.get_tesseract_version()
                logger.info(f"Tier A (pytesseract) verified successfully: {cmd}")
                return True
            return False
        except Exception as e:
            logger.debug(f"Tier A (pytesseract) probe failed: {e}")
            return False

    def _extract_pytesseract(self, image: Any, timeout: float) -> Optional[str]:
        """Executes pytesseract with grayscale preprocessing and subprocess timeout containment."""
        import pytesseract
        from PIL import ImageEnhance

        gray = image.convert("L")
        enhanced = ImageEnhance.Contrast(gray).enhance(1.5)

        text = pytesseract.image_to_string(
            enhanced,
            config="--psm 3 --oem 3 -l eng",
            timeout=timeout
        )
        return text.strip() if text else None

    # -------------------------------------------------------------------------
    # Tier B: easyocr Availability & Execution
    # -------------------------------------------------------------------------
    @property
    def is_easyocr_available(self) -> bool:
        if self._easyocr_available is None:
            self._easyocr_available = self._probe_easyocr()
        return self._easyocr_available

    def _probe_easyocr(self) -> bool:
        """Verifies easyocr and torch packages without triggering model downloads."""
        try:
            import easyocr
            import torch

            model_dir = Path.home() / ".EasyOCR" / "model"
            has_cached_weights = model_dir.exists() and any(model_dir.glob("*.pth"))

            if has_cached_weights or self.enable_easyocr_download:
                logger.info("Tier B (easyocr) verified available.")
                return True
            logger.debug("Tier B (easyocr) skipped: weights not cached locally.")
            return False
        except Exception as e:
            logger.debug(f"Tier B (easyocr) probe failed: {e}")
            return False

    def _get_easyocr_reader(self) -> Any:
        if self._easyocr_reader is None:
            import easyocr
            self._easyocr_reader = easyocr.Reader(
                ["en"],
                gpu=False,
                download_enabled=self.enable_easyocr_download
            )
        return self._easyocr_reader

    def _extract_easyocr(self, image_path: str, timeout: float) -> Optional[str]:
        """Executes easyocr in an isolated thread with timeout containment."""
        reader = self._get_easyocr_reader()

        def _read() -> str:
            results = reader.readtext(image_path, detail=0)
            return " ".join(results).strip()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_read)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                logger.warning(f"EasyOCR execution timed out after {timeout}s.")
                executor.shutdown(wait=False, cancel_futures=True)
                return None

    # -------------------------------------------------------------------------
    # Tier C: DOM SVG / Canvas Text Extraction + PIL Image Contrast Heuristic
    # -------------------------------------------------------------------------
    def _extract_dom_svg_canvas(self, rendered_dom: str) -> str:
        """
        Extracts embedded textual elements from SVG tags, Canvas accessibility
        attributes/fallbacks, and high-signal promotional DOM containers.
        """
        if not rendered_dom:
            return ""

        extracted: List[str] = []

        # 1. SVG text nodes (<text>, <tspan>, <title>, <desc>)
        svg_matches = re.findall(r"<svg\b[^>]*>(.*?)</svg>", rendered_dom, re.DOTALL | re.IGNORECASE)
        for svg_body in svg_matches:
            tags = re.findall(
                r"<(?:text|tspan|title|desc)\b[^>]*>(.*?)</(?:text|tspan|title|desc)>",
                svg_body,
                re.DOTALL | re.IGNORECASE
            )
            for t in tags:
                clean = re.sub(r"<[^>]+>", " ", t).strip()
                if clean:
                    extracted.append(html.unescape(clean))

            attrs = re.findall(r"\b(?:aria-label|alt|title)=['\"]([^'\"]+)['\"]", svg_body, re.IGNORECASE)
            for a in attrs:
                if a.strip():
                    extracted.append(html.unescape(a.strip()))

        # 2. HTML5 Canvas inner fallbacks and semantic data attributes
        canvas_matches = re.findall(r"<canvas\b([^>]*)>(.*?)</canvas>", rendered_dom, re.DOTALL | re.IGNORECASE)
        for attrs_str, inner_html in canvas_matches:
            clean_inner = re.sub(r"<[^>]+>", " ", inner_html).strip()
            if clean_inner:
                extracted.append(html.unescape(clean_inner))

            c_attrs = re.findall(
                r"\b(?:aria-label|data-text|data-title|data-label|title)=['\"]([^'\"]+)['\"]",
                attrs_str,
                re.IGNORECASE
            )
            for ca in c_attrs:
                if ca.strip():
                    extracted.append(html.unescape(ca.strip()))

        # 3. Dedicated promotional badges and alerts in rendered DOM
        promo_matches = re.findall(
            r"<(?:div|span|p|h[1-6]|section|header)\b[^>]*(?:class|id)=['\"][^'\"]*(?:promo|badge|voucher|discount|coupon|banner|alert|maintenance|announcement)[^'\"]*['\"][^>]*>(.*?)</(?:div|span|p|h[1-6]|section|header)>",
            rendered_dom,
            re.DOTALL | re.IGNORECASE
        )
        for pm in promo_matches:
            clean_pm = re.sub(r"<[^>]+>", " ", pm).strip()
            if clean_pm and len(clean_pm) <= 300:
                extracted.append(html.unescape(clean_pm))

        # Deduplicate while preserving sequence
        seen = set()
        deduped = []
        for line in extracted:
            normalized = " ".join(line.split())
            if normalized and normalized.lower() not in seen:
                seen.add(normalized.lower())
                deduped.append(normalized)

        return "\n".join(deduped)

    def _analyze_image_contrast_and_edges(self, image: Any) -> Tuple[bool, float, float]:
        """
        Analyzes image luminance variance and edge gradient density using native PIL.
        Returns: (visual_text_present, edge_density, contrast_variance)
        """
        from PIL import ImageFilter, ImageStat

        gray = image.convert("L")
        stat = ImageStat.Stat(gray)
        contrast_variance = float(stat.var[0])

        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        edge_mean = float(edge_stat.mean[0])
        edge_density = edge_mean / 255.0

        # Text requires both luminance variance and sharp edge gradients
        visual_text_present = (contrast_variance >= 50.0 and edge_mean >= 1.8)

        return visual_text_present, edge_density, contrast_variance

    # -------------------------------------------------------------------------
    # Text Post-Processing & Entity Extraction
    # -------------------------------------------------------------------------
    def post_process_text(self, text: str) -> Dict[str, Any]:
        """Extracts voucher codes, key phrases, zero-dollar status, and copay amounts."""
        if not text:
            return {
                "key_phrases": [],
                "voucher_codes": [],
                "has_zero_dollar_phrase": False,
                "has_voucher_applied": False,
                "has_maintenance_phrase": False,
                "has_copay_phrase": False,
                "copay_amount_usd": None,
                "snippet": ""
            }

        # 1. Voucher codes extraction
        raw_codes = VOUCHER_CODE_REGEX.findall(text)
        voucher_codes = [
            c for c in dict.fromkeys(raw_codes)
            if c.lower() not in VOUCHER_STOPWORDS and len(c) >= 4
        ]

        # 2. Key phrases extraction
        detected_phrases: List[str] = []
        has_zero_dollar = False
        has_voucher_applied = False
        has_maintenance = False
        has_copay = False

        for category, patterns in KEY_PHRASE_PATTERNS.items():
            for p in patterns:
                matches = re.findall(p, text, re.IGNORECASE)
                if matches:
                    for m in matches:
                        clean_m = " ".join(m.split()) if isinstance(m, str) else str(m)
                        if clean_m and clean_m.lower() not in [dp.lower() for dp in detected_phrases]:
                            detected_phrases.append(clean_m)

                    if category == "zero_dollar_discount":
                        has_zero_dollar = True
                    elif category == "voucher_applied":
                        has_voucher_applied = True
                    elif category == "maintenance":
                        has_maintenance = True
                    elif category == "copay_or_partial":
                        has_copay = True

        # 3. Price and Copay numerical extraction
        copay_amount: Optional[float] = None
        prices = PRICE_REGEX.findall(text)
        for p_str in prices:
            try:
                val = float(p_str.replace("$", "").strip())
                if val == 0.0:
                    has_zero_dollar = True
                elif val > 0.0 and has_copay:
                    copay_amount = val
            except ValueError:
                pass

        # 4. Truncate snippet to strictly <= 500 characters
        snippet = " ".join(text.split())[:500]

        return {
            "key_phrases": detected_phrases,
            "voucher_codes": voucher_codes,
            "has_zero_dollar_phrase": has_zero_dollar,
            "has_voucher_applied": has_voucher_applied,
            "has_maintenance_phrase": has_maintenance,
            "has_copay_phrase": has_copay,
            "copay_amount_usd": copay_amount,
            "snippet": snippet
        }

    # -------------------------------------------------------------------------
    # Progressive Orchestrator
    # -------------------------------------------------------------------------
    def extract_text(
        self,
        image_source: Optional[Union[str, Path, bytes, Any]] = None,
        rendered_dom: str = "",
        timeout: Optional[float] = None
    ) -> OCRResult:
        """
        Progressively extracts text from image and DOM with automatic failover.
        Safe against corrupt binaries, timeouts, and missing OS tools.
        """
        t0 = time.perf_counter()
        active_timeout = timeout or self.timeout_seconds

        pil_image = None
        visual_text_present = False
        edge_density = 0.0
        contrast_variance = 0.0

        # 1. Load and audit image safely if provided
        if image_source is not None:
            try:
                from PIL import Image, UnidentifiedImageError

                if isinstance(image_source, (str, Path)):
                    p = Path(image_source)
                    if p.is_file():
                        if p.stat().st_size == 0:
                            raise UnidentifiedImageError("Empty image file")
                        pil_image = Image.open(str(p))
                elif isinstance(image_source, bytes):
                    if len(image_source) == 0:
                        raise UnidentifiedImageError("Empty bytes")
                    pil_image = Image.open(io.BytesIO(image_source))
                elif hasattr(image_source, "convert"):
                    pil_image = image_source

                if pil_image:
                    visual_text_present, edge_density, contrast_variance = (
                        self._analyze_image_contrast_and_edges(pil_image)
                    )

            except UnidentifiedImageError:
                logger.warning("OCR Engine encountered corrupt image binary.")
                return OCRResult(
                    method="empty_fallback",
                    status="corrupt_image",
                    text="",
                    snippet="",
                    execution_time_ms=(time.perf_counter() - t0) * 1000
                )
            except Exception as img_err:
                if "DecompressionBombError" in type(img_err).__name__:
                    logger.warning("OCR Engine detected decompression bomb attack.")
                    return OCRResult(
                        method="empty_fallback",
                        status="decompression_bomb",
                        text="",
                        snippet="",
                        execution_time_ms=(time.perf_counter() - t0) * 1000
                    )
                logger.debug(f"Image load warning: {img_err}")

        # 2. Tier A: pytesseract execution
        if self.is_tesseract_available and pil_image:
            try:
                raw_text = self._extract_pytesseract(pil_image, timeout=active_timeout)
                if raw_text:
                    post = self.post_process_text(raw_text)
                    return OCRResult(
                        method="pytesseract",
                        status="success",
                        text=raw_text,
                        visual_text_present=visual_text_present,
                        edge_density=edge_density,
                        contrast_variance=contrast_variance,
                        confidence=0.95 if post["has_zero_dollar_phrase"] else 0.85,
                        execution_time_ms=(time.perf_counter() - t0) * 1000,
                        **post
                    )
            except Exception as e:
                logger.warning(f"Tier A (pytesseract) failed: {e}. Falling to Tier B...")

        # 3. Tier B: easyocr execution
        if self.is_easyocr_available and isinstance(image_source, (str, Path)):
            try:
                raw_text = self._extract_easyocr(str(image_source), timeout=active_timeout)
                if raw_text:
                    post = self.post_process_text(raw_text)
                    return OCRResult(
                        method="easyocr",
                        status="success",
                        text=raw_text,
                        visual_text_present=visual_text_present,
                        edge_density=edge_density,
                        contrast_variance=contrast_variance,
                        confidence=0.90 if post["has_zero_dollar_phrase"] else 0.80,
                        execution_time_ms=(time.perf_counter() - t0) * 1000,
                        **post
                    )
            except Exception as e:
                logger.warning(f"Tier B (easyocr) failed: {e}. Falling to Tier C...")

        # 4. Tier C: DOM SVG/Canvas extraction + PIL edge correlation
        dom_text = self._extract_dom_svg_canvas(rendered_dom)
        if dom_text or visual_text_present:
            post = self.post_process_text(dom_text)

            confidence = 0.50
            if post["has_zero_dollar_phrase"]:
                confidence = 0.85 if visual_text_present else 0.70
            elif visual_text_present:
                confidence = 0.65

            return OCRResult(
                method="dom_svg_contrast_heuristic",
                status="fallback",
                text=dom_text,
                visual_text_present=visual_text_present,
                edge_density=edge_density,
                contrast_variance=contrast_variance,
                confidence=confidence,
                execution_time_ms=(time.perf_counter() - t0) * 1000,
                **post
            )

        # 5. Empty Fallback
        return OCRResult(
            method="empty_fallback",
            status="empty",
            text="",
            snippet="",
            visual_text_present=visual_text_present,
            edge_density=edge_density,
            contrast_variance=contrast_variance,
            confidence=0.10,
            execution_time_ms=(time.perf_counter() - t0) * 1000
        )


_GLOBAL_OCR_ENGINE: Optional[ProgressiveOCREngine] = None

def get_ocr_engine() -> ProgressiveOCREngine:
    """Returns the process-wide singleton ProgressiveOCREngine instance."""
    global _GLOBAL_OCR_ENGINE
    if _GLOBAL_OCR_ENGINE is None:
        _GLOBAL_OCR_ENGINE = ProgressiveOCREngine()
    return _GLOBAL_OCR_ENGINE


def extract_ocr_text(
    image_source: Optional[Union[str, Path, bytes, Any]] = None,
    rendered_dom: str = "",
    timeout: Optional[float] = None
) -> OCRResult:
    """Convenience helper to extract OCR text via the global progressive engine."""
    return get_ocr_engine().extract_text(image_source=image_source, rendered_dom=rendered_dom, timeout=timeout)
