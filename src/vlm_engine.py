"""
CertPulse Multimodal VLM Semantic Gate, 3-Tier Progressive OCR & Heuristic Fallback Engine.
(Backward-Compatible Facade).

Modularized into src/vlm/ subpackage:
- src.vlm.models: Pydantic schemas (VLMSemanticVerdict, OCRResult) and regex registries
- src.vlm.ocr_engine: 3-tier progressive OCR engine (pytesseract -> easyocr -> PIL)
- src.vlm.provider_adapters: Frontier vision adapters (Claude, GPT-4o, Gemini)
- src.vlm.heuristic: Deterministic heuristic fallback evaluator
- src.vlm: Master gate evaluate_vlm_semantic_gate()
"""

from src.vlm import (
    evaluate_vlm_semantic_gate,
    VLMSemanticVerdict,
    OCRResult,
    OCRMethod,
    OCRStatus,
    RegistrationStatus,
    ProgressiveOCREngine,
    get_ocr_engine,
    extract_ocr_text,
    build_vlm_user_prompt,
    VLMProviderAdapters,
    evaluate_visual_semantics_heuristic,
    extract_detected_brand,
    extract_cta,
    KNOWN_BRANDS,
    VLM_SYSTEM_INSTRUCTION,
    KEY_PHRASE_PATTERNS,
    VOUCHER_CODE_REGEX,
    VOUCHER_STOPWORDS,
    PRICE_REGEX,
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
