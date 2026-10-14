from __future__ import annotations
import os
from pathlib import Path
from typing import Optional


class PDFEscalationEngine:
    """Interface for escalating suspicious PDF pages."""

    def escalate_page(self, pdf_path: Path, page_num: int) -> Optional[str]:
        raise NotImplementedError


class GeminiVisionPDFExtractor(PDFEscalationEngine):
    """
    Selective Gemini Multimodal Document Escalator.
    Only called when local extraction identifies suspicious pages and API key is present.
    Routes through ModelGateway control plane with atomic key leasing and official stealth SDK headers.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def escalate_page(self, pdf_path: Path, page_num: int) -> Optional[str]:
        """
        [DISABLED BY SYSTEM POLICY]
        PDF vision extraction via Google API is disabled by TTS-only policy.
        """
        # ponytail: root deadbolt - multimodal PDF API calls disabled
        raise RuntimeError(
            "PDF vision extraction via Google API is disabled by TTS-only policy. "
            "All OCR/extraction must be performed offline or inside Antigravity."
        )


