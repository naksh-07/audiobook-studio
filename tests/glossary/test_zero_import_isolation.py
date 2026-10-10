"""
Zero-Import Architectural Isolation Test for Glossary Subsystem (Room 1.5)
==========================================================================
Uses Python's AST parser to inspect every module in audiobook_factory/glossary/
and strictly assert that the standalone glossary & chapter metadata core has:
1. ZERO imports from downstream audio (audiobook_factory.audio, FFmpeg, LUFS)
2. ZERO imports from downstream TTS (audiobook_factory.tts)
3. ZERO imports from downstream screenplay/dramaturgy (audiobook_factory.screenplay, audiobook_factory.dramaturgy)
4. ZERO unmetered network requests (urllib.request, requests, httpx, aiohttp)
"""

import ast
import unittest
from pathlib import Path
from typing import List, Tuple

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
GLOSSARY_DIR = WORKSPACE_DIR / "audiobook_factory" / "glossary"

FORBIDDEN_IMPORT_PREFIXES = {
    "audiobook_factory.audio",
    "audiobook_factory.tts",
    "audiobook_factory.screenplay",
    "audiobook_factory.dramaturgy",
    "audiobook_factory.cinematic",
    "audiobook_factory.sound_bank",
    "audiobook_factory.ffmpeg_agent",
    "audiobook_factory.mastering",
    "pyaudio",
    "sounddevice",
    "alsaaudio",
    "urllib.request",
    "requests",
    "httpx",
    "aiohttp",
}


def get_all_imports(tree: ast.AST) -> List[Tuple[int, str]]:
    """Returns list of (lineno, imported_module_name) from an AST."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append((node.lineno, module))
    return imports


class TestZeroImportIsolation(unittest.TestCase):
    def test_01_assert_zero_forbidden_imports_in_glossary_core(self):
        """Validates that Room 1.5 standalone glossary modules have 0 audio/tts/screenplay/network imports."""
        py_files = list(GLOSSARY_DIR.glob("*.py"))
        self.assertGreater(len(py_files), 0, "No Python files found in audiobook_factory/glossary")

        violations = []
        for file_path in py_files:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
            imports = get_all_imports(tree)

            for lineno, mod_name in imports:
                for forbidden in FORBIDDEN_IMPORT_PREFIXES:
                    if mod_name == forbidden or mod_name.startswith(forbidden + "."):
                        violations.append(
                            f"{file_path.name}:{lineno} imports '{mod_name}' (violates isolation rule: forbidden '{forbidden}')"
                        )

        self.assertEqual(
            violations,
            [],
            f"Found architectural boundary violations in audiobook_factory/glossary/:\n"
            + "\n".join(violations),
        )

    def test_02_glossary_manager_routes_exclusively_through_control_plane(self):
        """Validates that gateway_bridge routes through ModelGateway and never calls raw API endpoints."""
        bridge_file = GLOSSARY_DIR / "gateway_bridge.py"
        source = bridge_file.read_text(encoding="utf-8")
        self.assertIn("from audiobook_factory.core.models.gateway import get_model_gateway", source)
        self.assertIn("execute_glossary_llm", source)
        self.assertNotIn("urllib.request", source)
        self.assertNotIn("requests.post", source)
        self.assertNotIn("httpx.post", source)
