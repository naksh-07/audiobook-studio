#!/usr/bin/env python3
"""
Test Suite: Zero-Import Isolation & Static AST Guardrails for Extraction Subsystem.
Verifies that audiobook_factory.extraction remains 100% decoupled and standalone,
with zero static or dynamic imports of downstream studio subsystems
(translation, dramaturgy, screenplay, tts, mastering, orchestrator, dispatcher).
"""

import ast
import os
import sys
import subprocess
from pathlib import Path
import pytest

FORBIDDEN_SUBSYSTEMS = {
    "translation",
    "dramaturgy",
    "screenplay",
    "tts",
    "mastering",
    "orchestrator",
    "dispatcher",
    "soundscape",
    "book_bible",
    "cinema_audio_engine",
    "mastering_analyzer",
    "mastering_qc",
    "dialogue_editing",
    "gate_auditor",
}


class TestZeroImportIsolation:
    """Rigorous architectural isolation verification for audiobook_factory.extraction."""

    @classmethod
    def setup_class(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent.parent
        cls.extraction_dir = cls.repo_root / "audiobook_factory" / "extraction"
        assert cls.extraction_dir.is_dir(), f"Extraction dir not found at {cls.extraction_dir}"

    def test_01_ast_static_zero_downstream_imports(self):
        """
        Scans all Python source files in audiobook_factory/extraction/ using Python's AST parser.
        Ensures zero import statements reference any downstream studio subsystem.
        """
        py_files = list(self.extraction_dir.rglob("*.py"))
        assert len(py_files) >= 10, f"Expected at least 10 python files in extraction, found {len(py_files)}"

        violations = []

        for py_path in py_files:
            rel_path = py_path.relative_to(self.repo_root)
            content = py_path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content, filename=str(py_path))
            except SyntaxError as e:
                violations.append(f"Syntax error in {rel_path}: {e}")
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        parts = alias.name.split(".")
                        for forbidden in FORBIDDEN_SUBSYSTEMS:
                            if forbidden in parts:
                                violations.append(
                                    f"[{rel_path}:{node.lineno}] Forbidden 'import {alias.name}' detected"
                                )

                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    parts = module.split(".")
                    for forbidden in FORBIDDEN_SUBSYSTEMS:
                        if forbidden in parts:
                            violations.append(
                                f"[{rel_path}:{node.lineno}] Forbidden 'from {module} import ...' detected"
                            )

                    # Check for imported symbol names matching forbidden subsystems
                    for alias in node.names:
                        if alias.name in FORBIDDEN_SUBSYSTEMS:
                            violations.append(
                                f"[{rel_path}:{node.lineno}] Forbidden symbol imported: {alias.name}"
                            )

        assert not violations, (
            f"Zero-Import Isolation Failure: {len(violations)} forbidden downstream import(s) detected:\n"
            + "\n".join(violations)
        )

    def test_02_runtime_import_purity(self):
        """
        Spawns a clean subprocess importing audiobook_factory.extraction and inspects sys.modules.
        Ensures that importing extraction does not load any downstream modules into memory.
        """
        verification_script = """
import sys
import audiobook_factory.extraction

forbidden = {
    'translation', 'dramaturgy', 'screenplay', 'tts', 'mastering',
    'orchestrator', 'dispatcher', 'soundscape', 'book_bible'
}

loaded_forbidden = [
    mod_name for mod_name in sys.modules
    if any(f in mod_name.split('.') for f in forbidden)
]

if loaded_forbidden:
    print(f"FAILED: Leaked modules: {loaded_forbidden}")
    sys.exit(1)

print("SUCCESS")
sys.exit(0)
"""
        result = subprocess.run(
            [sys.executable, "-c", verification_script],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"Runtime import purity failed (exit code {result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        assert "SUCCESS" in result.stdout

    def test_03_cli_import_purity(self):
        """
        Verifies that running the extraction CLI tool does not pull downstream studio modules into memory.
        """
        cli_test_script = """
import sys
import subprocess

code = '''
import sys
from audiobook_factory.extraction import cli

forbidden = {
    'translation', 'dramaturgy', 'screenplay', 'tts', 'mastering',
    'orchestrator', 'dispatcher', 'soundscape', 'book_bible'
}

loaded_forbidden = [
    mod_name for mod_name in sys.modules
    if any(f in mod_name.split('.') for f in forbidden)
]

if loaded_forbidden:
    print(f"FAILED: Leaked in CLI: {loaded_forbidden}")
    sys.exit(1)

print("CLI_ISOLATION_OK")
sys.exit(0)
'''

proc = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
print(proc.stdout)
if proc.returncode != 0:
    print(proc.stderr, file=sys.stderr)
sys.exit(proc.returncode)
"""
        result = subprocess.run(
            [sys.executable, "-c", cli_test_script],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"CLI runtime purity failed (exit code {result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        assert "CLI_ISOLATION_OK" in result.stdout

    def test_04_direct_submodule_import_purity(self):
        """
        Imports every major submodule of audiobook_factory.extraction in a clean process
        and verifies none drag in downstream modules.
        """
        submodules_script = """
import sys
from audiobook_factory.extraction import (
    contracts,
    engine,
    normalizer,
    segmenter,
    quality_gate,
)
from audiobook_factory.extraction.parsers import epub, text
from audiobook_factory.extraction.parsers.pdf import forensic_engine, layout_reconstructor

forbidden = {
    'translation', 'dramaturgy', 'screenplay', 'tts', 'mastering',
    'orchestrator', 'dispatcher', 'soundscape', 'book_bible'
}

loaded_forbidden = [
    mod_name for mod_name in sys.modules
    if any(f in mod_name.split('.') for f in forbidden)
]

if loaded_forbidden:
    print(f"FAILED: Leaked modules: {loaded_forbidden}")
    sys.exit(1)

print("ALL_SUBMODULES_CLEAN")
sys.exit(0)
"""
        result = subprocess.run(
            [sys.executable, "-c", submodules_script],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"Submodule import purity failed (exit code {result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        assert "ALL_SUBMODULES_CLEAN" in result.stdout
