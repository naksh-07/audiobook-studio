"""
Zero-Import Architectural Isolation Test for Translation Subsystem (Option D)
=============================================================================
Uses Python's AST parser to inspect every module in audiobook_factory/translation/
and strictly assert that the standalone translation core has ZERO imports from:
- audiobook_factory.audio (FFmpeg, mastering, LUFS)
- audiobook_factory.tts (Gemini TTS, voice dispatcher)
- audiobook_factory.screenplay (Screenplay cleaner, script builder)
- audiobook_factory.cinematic (Sound bank, Foley)
- Audio hardware libraries (pyaudio, sounddevice)
"""

import ast
import unittest
from pathlib import Path
from typing import List, Set, Tuple

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
TRANSLATION_DIR = WORKSPACE_DIR / "audiobook_factory" / "translation"

FORBIDDEN_IMPORT_PREFIXES = {
    "audiobook_factory.audio",
    "audiobook_factory.tts",
    "audiobook_factory.screenplay",
    "audiobook_factory.cinematic",
    "audiobook_factory.sound_bank",
    "audiobook_factory.ffmpeg_agent",
    "audiobook_factory.mastering",
    "pyaudio",
    "sounddevice",
    "alsaaudio",
}

STANDALONE_CORE_FILES = {
    "contracts.py",
    "chunker.py",
    "parity_gate.py",
    "alignment.py",
    "prompt_builder.py",
    "engine.py",
    "cli.py",
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
    def test_01_assert_zero_forbidden_imports_in_standalone_core(self):
        """Validates that Option D standalone translation modules have 0 audio/tts/screenplay imports."""
        py_files = [f for f in TRANSLATION_DIR.glob("*.py") if f.name in STANDALONE_CORE_FILES]
        self.assertEqual(len(py_files), len(STANDALONE_CORE_FILES), "All standalone core files must exist")

        violations = []
        for py_file in py_files:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            file_imports = get_all_imports(tree)

            for lineno, imported_mod in file_imports:
                for forbidden in FORBIDDEN_IMPORT_PREFIXES:
                    if imported_mod == forbidden or imported_mod.startswith(forbidden + "."):
                        violations.append(
                            f"{py_file.name}:{lineno} imports forbidden dependency '{imported_mod}'"
                        )

        if violations:
            msg = (
                f"\nArchitectural Isolation Breach: Found {len(violations)} forbidden dependencies:\n"
                + "\n".join(f"  - {v}" for v in violations)
            )
            self.fail(msg)

    def test_02_engine_instantiable_without_key(self):
        """Verifies TranslationEngine can be imported and instantiated without crashing or needing API keys."""
        from audiobook_factory.translation import TranslationEngine, TranslationRequest
        engine = TranslationEngine()
        self.assertIsNotNone(engine)
        self.assertIsNotNone(engine.chunker)
        self.assertIsNotNone(engine.parity_gate)

    def test_03_assert_zero_forbidden_imports_across_all_translation_modules(self):
        """Recursively validates that ALL modules in audiobook_factory/translation/ have 0 audio/tts/screenplay imports."""
        all_py_files = list(TRANSLATION_DIR.rglob("*.py"))
        self.assertGreater(len(all_py_files), 10, "Must scan all translation modules")

        violations = []
        for py_file in all_py_files:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            file_imports = get_all_imports(tree)

            for lineno, imported_mod in file_imports:
                for forbidden in FORBIDDEN_IMPORT_PREFIXES:
                    if imported_mod == forbidden or imported_mod.startswith(forbidden + "."):
                        rel_path = py_file.relative_to(TRANSLATION_DIR)
                        violations.append(
                            f"{rel_path}:{lineno} imports forbidden dependency '{imported_mod}'"
                        )

        if violations:
            msg = (
                f"\nArchitectural Isolation Breach: Found {len(violations)} forbidden dependencies across translation/:\n"
                + "\n".join(f"  - {v}" for v in violations)
            )
            self.fail(msg)


if __name__ == "__main__":
    unittest.main()
