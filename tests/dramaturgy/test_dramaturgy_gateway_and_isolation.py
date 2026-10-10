#!/usr/bin/env python3
"""
Test Suite: Dramaturgy Gateway Control Plane Integration & AST Isolation.
========================================================================
Validates:
1. execute_dramaturgy_llm routes calls through ModelGateway.
2. AST scan confirms zero direct unmetered HTTP imports (urllib.request, requests, httpx).
3. Studio certification fails closed on corrupted script JSON files.
"""

import ast
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from audiobook_factory.dramaturgy.gateway_bridge import execute_dramaturgy_llm
from audiobook_factory.certification.runner import StudioCertificationRunner


class TestDramaturgyGatewayAndIsolation:

    def test_01_execute_dramaturgy_llm_routes_via_model_gateway(self):
        """Verify execute_dramaturgy_llm calls ModelGateway.generate_text with expected kwargs."""
        mock_gateway = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"turns": [{"index": 1, "speaker": "Host_A", "text": "Testing gateway."}]}'
        mock_gateway.generate_text.return_value = mock_response

        with patch("audiobook_factory.core.models.gateway.get_model_gateway", return_value=mock_gateway):
            with patch.dict("os.environ", {"MOCK_OFFLINE": "0", "GEMINI_API_KEY": "AIzaSyTestKey123"}):
                res = execute_dramaturgy_llm(
                    prompt="Plan podcast turns",
                    system_instruction="You are a podcast host.",
                    task="screenplay",
                    model="gemini-2.5-flash",
                    json_mode=True,
                )

        assert mock_gateway.generate_text.called
        call_kwargs = mock_gateway.generate_text.call_args[1]
        assert call_kwargs["task"] == "screenplay"
        assert call_kwargs["model"] == "gemini-2.5-flash"
        assert call_kwargs["response_json"] is True
        assert isinstance(res, (dict, list))

    def test_02_execute_dramaturgy_llm_fails_closed(self):
        """Verify execute_dramaturgy_llm raises RuntimeError / fails closed when gateway error occurs."""
        mock_gateway = MagicMock()
        mock_gateway.generate_text.side_effect = RuntimeError("All keys exhausted")

        with patch("audiobook_factory.core.models.gateway.get_model_gateway", return_value=mock_gateway):
            with patch.dict("os.environ", {"MOCK_OFFLINE": "0", "GEMINI_API_KEY": "AIzaSyTestKey123"}):
                with pytest.raises(RuntimeError, match="All keys exhausted"):
                    execute_dramaturgy_llm(
                        prompt="Plan podcast turns",
                        task="screenplay",
                        json_mode=True,
                    )

    def test_03_ast_assert_zero_unmetered_http_imports(self):
        """AST check: ensure no direct urllib.request, requests, or httpx in dramaturgy, podcast, or adapters."""
        root_dir = Path(__file__).resolve().parent.parent.parent / "audiobook_factory"
        target_dirs = [
            root_dir / "dramaturgy",
            root_dir / "podcast",
            root_dir / "adapters",
            root_dir / "certification",
            root_dir / "packaging",
        ]

        forbidden = {"urllib.request", "requests", "httpx", "aiohttp"}
        violations = []

        for target in target_dirs:
            if not target.exists():
                continue
            for py_file in target.glob("**/*.py"):
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name in forbidden:
                                violations.append(f"{py_file.name}: import {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        mod = node.module or ""
                        if mod in forbidden or any(mod.startswith(f"{fb}.") for fb in forbidden):
                            violations.append(f"{py_file.name}: from {mod} import ...")

        assert not violations, f"Forbidden unmetered HTTP imports found: {violations}"

    def test_04_studio_certification_fails_closed_on_corrupt_script(self, tmp_path):
        """Verify Studio Certification fails closed (is_certified=False) if a script file is corrupt."""
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(parents=True)
        # Create corrupted JSON
        (scripts_dir / "chapter_001_script.json").write_text("{corrupted json!!", encoding="utf-8")
        (tmp_path / "extracted").mkdir()
        (tmp_path / "extracted" / "chapter_001.md").write_text("Chapter 1 text content " * 10, encoding="utf-8")

        report = StudioCertificationRunner.certify_project(
            project_dir=tmp_path,
            format_mode="audiobook",
        )

        assert report.is_certified is False
        p3 = report.pillars.get("P3_DRAMATURGY")
        assert p3 is not None
        assert p3.status == "FAILED"
        assert any("Could not read script" in f for f in p3.critical_findings)
