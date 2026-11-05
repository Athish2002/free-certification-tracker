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
    KEY_PHRASE_PATTERNS,
    KNOWN_BRANDS,
    PRICE_REGEX,
    VLM_SYSTEM_INSTRUCTION,
    VOUCHER_CODE_REGEX,
    VOUCHER_STOPWORDS,
    OCRMethod,
    OCRResult,
    OCRStatus,
    ProgressiveOCREngine,
    RegistrationStatus,
    VLMProviderAdapters,
    VLMSemanticVerdict,
    build_vlm_user_prompt,
    evaluate_visual_semantics_heuristic,
    evaluate_vlm_semantic_gate,
    extract_cta,
    extract_detected_brand,
    extract_ocr_text,
    get_ocr_engine,
)

__all__ = [
    "KEY_PHRASE_PATTERNS",
    "KNOWN_BRANDS",
    "PRICE_REGEX",
    "VLM_SYSTEM_INSTRUCTION",
    "VOUCHER_CODE_REGEX",
    "VOUCHER_STOPWORDS",
    "OCRMethod",
    "OCRResult",
    "OCRStatus",
    "ProgressiveOCREngine",
    "RegistrationStatus",
    "VLMProviderAdapters",
    "VLMSemanticVerdict",
    "build_vlm_user_prompt",
    "evaluate_visual_semantics_heuristic",
    "evaluate_vlm_semantic_gate",
    "extract_cta",
    "extract_detected_brand",
    "extract_ocr_text",
    "get_ocr_engine",
]
