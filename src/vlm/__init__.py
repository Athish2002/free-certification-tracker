"""
CertPulse Multimodal VLM Semantic Gate, 3-Tier Progressive OCR & Heuristic Fallback Package.
Implements Tier 3 of the Authenticity Architecture.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from src.vlm.models import (
    OCRMethod,
    OCRResult,
    OCRStatus,
    RegistrationStatus,
    VLMSemanticVerdict,
    KEY_PHRASE_PATTERNS,
    PRICE_REGEX,
    VLM_SYSTEM_INSTRUCTION,
    VOUCHER_CODE_REGEX,
    VOUCHER_STOPWORDS,
)
from src.vlm.ocr_engine import (
    ProgressiveOCREngine,
    extract_ocr_text,
    get_ocr_engine,
)
from src.vlm.provider_adapters import (
    VLMProviderAdapters,
    build_vlm_user_prompt,
)
from src.vlm.heuristic import (
    KNOWN_BRANDS,
    evaluate_visual_semantics_heuristic,
    extract_cta,
    extract_detected_brand,
)

logger = logging.getLogger("certpulse.vlm")


def evaluate_vlm_semantic_gate(
    offer_id: str = "",
    url: str = "",
    dom_text: str = "",
    dom_title: str = "",
    screenshot_path: Optional[str] = None,
    screenshot_bytes: Optional[bytes] = None,
    platform: str = "",
    offer_data: Optional[Dict[str, Any]] = None,
    timeout_seconds: float = 10.0
) -> VLMSemanticVerdict:
    """
    Main Entry Point: Evaluates visual semantics of a captured screenshot and DOM.
    Checks environment for live VLM credentials (Claude, GPT-4o, Gemini).
    If credentials exist, attempts live multimodal inference with timeout containment.
    If credentials are absent, invalid, or API call fails, seamlessly falls back to
    evaluate_visual_semantics_heuristic() to guarantee 100% offline test execution.
    """
    # 1. Load screenshot bytes if only path was provided
    if not screenshot_bytes and screenshot_path:
        p = Path(screenshot_path)
        if not p.is_absolute():
            p = Path(__file__).resolve().parent.parent.parent / screenshot_path
        if p.exists():
            try:
                screenshot_bytes = p.read_bytes()
            except Exception as e:
                logger.debug(f"Could not read screenshot {screenshot_path}: {e}")

    # 2. Extract OCR snippet and badge pHash match if components are available
    ocr_snippet: Optional[str] = None
    badge_phash_matched: bool = False

    try:
        from src.visual_hasher import match_badge_phash
        if screenshot_path or screenshot_bytes:
            badge_phash_matched = match_badge_phash(
                image_path=screenshot_path,
                image_bytes=screenshot_bytes,
                platform=platform
            )
    except Exception:
        badge_phash_matched = False

    try:
        if screenshot_path or screenshot_bytes or dom_text:
            ocr_res = extract_ocr_text(
                image_source=screenshot_bytes or screenshot_path,
                rendered_dom=dom_text
            )
            ocr_snippet = ocr_res.snippet or None
    except Exception:
        ocr_snippet = None

    # 3. Check for external VLM API Keys
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    has_live_keys = bool(anthropic_key or openai_key or gemini_key)
    has_valid_image = bool(screenshot_bytes and len(screenshot_bytes) >= 4096)

    # 4. Attempt Live VLM Inference if API Key and Valid Image Present
    if has_live_keys and has_valid_image:
        title = (offer_data.get("title") if offer_data else "") or dom_title or offer_id
        user_prompt = build_vlm_user_prompt(
            offer_id=offer_id,
            title=title,
            platform=platform,
            url=url,
            ocr_snippet=ocr_snippet,
            badge_phash_matched=badge_phash_matched
        )

        import httpx

        # A. Anthropic Claude 3.5 Sonnet
        if anthropic_key:
            try:
                payload = VLMProviderAdapters.build_claude_payload(screenshot_bytes, user_prompt)
                headers = {
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                with httpx.Client(timeout=timeout_seconds) as client:
                    resp = client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_content = data["content"][0]["text"]
                        parsed = VLMProviderAdapters.clean_json_response(raw_content)
                        parsed["model_used"] = "claude-3-5-sonnet"
                        parsed["badge_phash_matched"] = badge_phash_matched
                        parsed["ocr_text_snippet"] = ocr_snippet
                        return VLMSemanticVerdict.model_validate(parsed)
            except Exception as e:
                logger.warning(f"Claude 3.5 live VLM inference failed: {e}. Falling back to heuristic engine.")

        # B. OpenAI GPT-4o
        elif openai_key:
            try:
                payload = VLMProviderAdapters.build_gpt4o_payload(screenshot_bytes, user_prompt)
                headers = {
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json"
                }
                with httpx.Client(timeout=timeout_seconds) as client:
                    resp = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_content = data["choices"][0]["message"]["content"]
                        parsed = VLMProviderAdapters.clean_json_response(raw_content)
                        parsed["model_used"] = "gpt-4o"
                        parsed["badge_phash_matched"] = badge_phash_matched
                        parsed["ocr_text_snippet"] = ocr_snippet
                        return VLMSemanticVerdict.model_validate(parsed)
            except Exception as e:
                logger.warning(f"GPT-4o live VLM inference failed: {e}. Falling back to heuristic engine.")

        # C. Google Gemini 2.0 Flash
        elif gemini_key:
            try:
                payload = VLMProviderAdapters.build_gemini_payload(screenshot_bytes, user_prompt)
                url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
                headers = {"Content-Type": "application/json"}
                with httpx.Client(timeout=timeout_seconds) as client:
                    resp = client.post(url_gemini, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_content = data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = VLMProviderAdapters.clean_json_response(raw_content)
                        parsed["model_used"] = "gemini-2.0-flash"
                        parsed["badge_phash_matched"] = badge_phash_matched
                        parsed["ocr_text_snippet"] = ocr_snippet
                        return VLMSemanticVerdict.model_validate(parsed)
            except Exception as e:
                logger.warning(f"Gemini 2.0 live VLM inference failed: {e}. Falling back to heuristic engine.")

    # 5. Seamless Deterministic Heuristic Fallback
    return evaluate_visual_semantics_heuristic(
        offer_id=offer_id,
        url=url,
        dom_text=dom_text,
        dom_title=dom_title,
        screenshot_path=screenshot_path,
        screenshot_bytes=screenshot_bytes,
        ocr_text=ocr_snippet,
        badge_phash_matched=badge_phash_matched,
        platform=platform,
        offer_data=offer_data
    )


__all__ = [
    "evaluate_vlm_semantic_gate",
    "VLMSemanticVerdict",
    "OCRResult",
    "OCRMethod",
    "OCRStatus",
    "RegistrationStatus",
    "ProgressiveOCREngine",
    "get_ocr_engine",
    "extract_ocr_text",
    "build_vlm_user_prompt",
    "VLMProviderAdapters",
    "evaluate_visual_semantics_heuristic",
    "extract_detected_brand",
    "extract_cta",
    "KNOWN_BRANDS",
    "VLM_SYSTEM_INSTRUCTION",
    "KEY_PHRASE_PATTERNS",
    "VOUCHER_CODE_REGEX",
    "VOUCHER_STOPWORDS",
    "PRICE_REGEX",
]
