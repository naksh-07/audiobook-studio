from __future__ import annotations
import os
import re
import json
import base64
import urllib.request
import urllib.error
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
        if not self.api_key:
            try:
                from audiobook_factory.key_manager import get_persistent_key_pool
                self.api_key = get_persistent_key_pool().get_key(service="text")
            except Exception:
                pass

    def escalate_page(self, pdf_path: Path, page_num: int) -> Optional[str]:
        """
        Extracts a single suspicious page via Gemini Multimodal document API.
        If pypdf is available, creates a single-page temporary PDF to minimize token usage.
        """
        try:
            import pypdf
            with open(pdf_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                if page_num > len(reader.pages):
                    return None

                writer = pypdf.PdfWriter()
                writer.add_page(reader.pages[page_num - 1])

                import io
                buf = io.BytesIO()
                writer.write(buf)
                buf.seek(0)
                page_bytes = buf.read()
        except Exception:
            return None

        # Build multimodal payload with single page PDF
        b64_data = base64.b64encode(page_bytes).decode("utf-8")
        prompt = (
            "Extract all text from this document page in strict, clean Markdown reading order.\n"
            "- Tables: Transcribe all tables into clean, structured Markdown table syntax with headers (| Col 1 | Col 2 |).\n"
            "- Mathematics: Transcribe all mathematical formulas, variables, and expressions into standard LaTeX syntax ($...$ for inline math, $$...$$ for display equations).\n"
            "- Structure: Preserve section headers (#, ##, ###), bullet lists, and figure/table captions.\n"
            "- Cleanliness: Strip running headers and page numbers. Do not summarize or omit text."
        )

        parts = [
            {"text": prompt},
            {"inlineData": {"mimeType": "application/pdf", "data": b64_data}},
        ]

        # 1. Primary path: ModelGateway Control Plane (Atomic Leasing & Stealth Headers)
        try:
            from audiobook_factory.core.models.gateway import get_model_gateway
            gateway = get_model_gateway()
            res = gateway.generate_text(
                prompt=prompt,
                task="extraction",
                parts=parts,
                user_id="extraction_worker",
                session_id=f"pdf_page_{page_num}",
                fast_mode=True,
            )
            text = res.text
            if text:
                text = re.sub(r"^```(?:markdown|md|text)?\s*\n?", "", text.strip(), flags=re.IGNORECASE)
                text = re.sub(r"\n?```\s*$", "", text.strip())
                text = re.sub(
                    r"^(?:sure[,!]?\s+|certainly[,!]?\s+)?(?:here|below)\s+is\s+the\s+(?:extracted|transcribed|ocr|markdown|prose)[^\n]*:\s*\n+",
                    "",
                    text.strip(),
                    flags=re.IGNORECASE,
                )
                return text.strip()
        except Exception:
            pass

        # 2. Offline / Direct API Key Fallback
        if not self.api_key:
            return None

        try:
            from audiobook_factory.model_manager import get_model_manager, TaskType
            from audiobook_factory.safety import get_universal_safety_settings
            from audiobook_factory.core.models.anti_ban_guard import get_stealth_sdk_headers
            model = get_model_manager().resolve_active_model(TaskType.EXTRACTION, api_key=self.api_key)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": parts}],
                "safetySettings": get_universal_safety_settings(),
            }
            headers = get_stealth_sdk_headers(self.api_key, provider="gemini")
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                text = re.sub(r"^```(?:markdown|md|text)?\s*\n?", "", text.strip(), flags=re.IGNORECASE)
                text = re.sub(r"\n?```\s*$", "", text.strip())
                text = re.sub(
                    r"^(?:sure[,!]?\s+|certainly[,!]?\s+)?(?:here|below)\s+is\s+the\s+(?:extracted|transcribed|ocr|markdown|prose)[^\n]*:\s*\n+",
                    "",
                    text.strip(),
                    flags=re.IGNORECASE,
                )
                return text.strip()
        except Exception:
            return None


