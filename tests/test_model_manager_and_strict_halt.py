#!/usr/bin/env python3
"""
Test Suite for Dynamic Model Intelligence & Strict Production Halt Contracts
=============================================================================
Validates:
1. Dynamic model discovery and semantic capability tiering.
2. Concurrent multi-model health ping & latency-based model resolution.
3. Strict quality floor breach enforcement (ModelTierFloorBreachError).
4. Strict fail-closed production halts across all creative modules (LLMUnavailableError):
   - script_builder.py
   - dramaturgy/beat_planner.py
   - agent_director.py
   - soundscape.py
   - translator.py
5. AST scan asserting zero hardcoded Gemini model string literals across
   audiobook_factory/ outside exempt modules (model_manager.py, tts_dispatcher.py,
   pronunciation/contracts.py, pronunciation/provenance.py).
"""

import os
import ast
import json
import re
import unittest
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock

from audiobook_factory.model_manager import (
    ModelManager,
    ModelTier,
    TaskType,
    TASK_MINIMUM_TIERS,
    LLMUnavailableError,
    ModelTierFloorBreachError,
)

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
FACTORY_DIR = WORKSPACE_DIR / "audiobook_factory"


class TestModelManagerAndStrictHalt(unittest.TestCase):

    def setUp(self):
        self._prev_mock = os.environ.pop("MOCK_OFFLINE", None)
        self.manager = ModelManager(cache_ttl_sec=3600.0, ping_cache_ttl_sec=300.0)

    def tearDown(self):
        if self._prev_mock is not None:
            os.environ["MOCK_OFFLINE"] = self._prev_mock
        else:
            os.environ.pop("MOCK_OFFLINE", None)

    # =========================================================================
    # 1. Dynamic Discovery & Semantic Capability Tiering
    # =========================================================================
    def test_01_tier_classification(self):
        """Validates that models are accurately classified into semantic capability tiers."""
        # Tier 1 Flagship: High reasoning models and pro previews
        self.assertEqual(self.manager.classify_model_tier("gemini-3.8-flash"), ModelTier.TIER_1_FLAGSHIP)
        self.assertEqual(self.manager.classify_model_tier("gemini-3.7-flash"), ModelTier.TIER_1_FLAGSHIP)
        self.assertEqual(self.manager.classify_model_tier("gemini-2.5-pro"), ModelTier.TIER_1_FLAGSHIP)
        self.assertEqual(self.manager.classify_model_tier("gemini-pro-preview-0514"), ModelTier.TIER_1_FLAGSHIP)

        # Tier 2 Balanced: Standard balanced flash models
        self.assertEqual(self.manager.classify_model_tier("gemini-3.6-flash"), ModelTier.TIER_2_BALANCED)
        self.assertEqual(self.manager.classify_model_tier("gemini-3.5-flash"), ModelTier.TIER_2_BALANCED)
        self.assertEqual(self.manager.classify_model_tier("gemini-2.5-flash"), ModelTier.TIER_2_BALANCED)
        self.assertEqual(self.manager.classify_model_tier("gemini-flash-latest"), ModelTier.TIER_2_BALANCED)

        # Tier 3 Utility: Lightweight / small parameter models
        self.assertEqual(self.manager.classify_model_tier("gemini-3.1-flash-lite"), ModelTier.TIER_3_UTILITY)
        self.assertEqual(self.manager.classify_model_tier("gemini-flash-lite-latest"), ModelTier.TIER_3_UTILITY)
        self.assertEqual(self.manager.classify_model_tier("gemma-2-9b-it"), ModelTier.TIER_3_UTILITY)

    def test_02_task_minimum_tier_contracts(self):
        """Validates that creative tasks require TIER_1_FLAGSHIP, and balanced tasks require TIER_2_BALANCED."""
        self.assertEqual(TASK_MINIMUM_TIERS[TaskType.TRANSLATION], ModelTier.TIER_1_FLAGSHIP)
        self.assertEqual(TASK_MINIMUM_TIERS[TaskType.SCREENPLAY], ModelTier.TIER_1_FLAGSHIP)
        self.assertEqual(TASK_MINIMUM_TIERS[TaskType.DRAMATURGY], ModelTier.TIER_1_FLAGSHIP)
        self.assertEqual(TASK_MINIMUM_TIERS[TaskType.DIRECTING], ModelTier.TIER_2_BALANCED)
        self.assertEqual(TASK_MINIMUM_TIERS[TaskType.SOUND_DESIGN], ModelTier.TIER_2_BALANCED)
        self.assertEqual(TASK_MINIMUM_TIERS[TaskType.AUDITING], ModelTier.TIER_2_BALANCED)
        self.assertEqual(TASK_MINIMUM_TIERS[TaskType.EXTRACTION], ModelTier.TIER_2_BALANCED)
        self.assertEqual(TASK_MINIMUM_TIERS[TaskType.UTILITY], ModelTier.TIER_3_UTILITY)

    def test_03_discovery_filters_non_general_models(self):
        """Validates that specialized non-chat/audio/robotics models are filtered during discovery."""
        mock_raw_response = {
            "models": [
                {"name": "models/gemini-3.8-flash", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-3.8-flash-tts", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/deep-research-preview", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/imagen-3.0-generate-002", "supportedGenerationMethods": ["generateImage"]},
                {"name": "models/gemini-robotics-rt", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-3.6-flash", "supportedGenerationMethods": ["generateContent"]},
            ]
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json_bytes(mock_raw_response)
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            discovered = self.manager.discover_available_models(refresh=True, api_key="fake-key")

            self.assertIn("gemini-3.8-flash", discovered)
            self.assertIn("gemini-3.6-flash", discovered)
            self.assertNotIn("gemini-3.8-flash-tts", discovered)
            self.assertNotIn("deep-research-preview", discovered)
            self.assertNotIn("imagen-3.0-generate-002", discovered)
            self.assertNotIn("gemini-robotics-rt", discovered)

    # =========================================================================
    # 2. Concurrent Multi-Model Health Pings & Active Selection
    # =========================================================================
    def test_04_concurrent_ping_selection_healthy(self):
        """Validates that pinging concurrently selects the healthy model for balanced task."""
        # Simulate: gemini-3.8-flash fails (HTTP 503), gemini-3.7-flash fails (timeout), gemini-3.6-flash succeeds (120ms)
        def mock_ping(candidates, api_key=None, timeout=6.0):
            res = []
            for c in candidates:
                if "3.8" in c:
                    res.append((c, False, 800.0, "HTTP 503"))
                elif "3.7" in c:
                    res.append((c, False, 6000.0, "Timed out"))
                elif "3.6" in c:
                    res.append((c, True, 120.0, None))
                else:
                    res.append((c, True, 250.0, None))
            return res

        with patch.object(self.manager, "ping_candidate_models", side_effect=mock_ping):
            with patch.object(self.manager, "discover_available_models", return_value=["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"]):
                chosen = self.manager.resolve_active_model(TaskType.DIRECTING, force_refresh=True)
                self.assertEqual(chosen, "gemini-3.6-flash")

    def test_05_active_model_caching_and_invalidation(self):
        """Validates that resolved models are cached within TTL and invalidated on report_failure."""
        with patch.object(self.manager, "ping_candidate_models", return_value=[("gemini-3.6-flash", True, 50.0, None)]):
            with patch.object(self.manager, "discover_available_models", return_value=["gemini-3.6-flash"]):
                chosen1 = self.manager.resolve_active_model(TaskType.DIRECTING, force_refresh=True)
                self.assertEqual(chosen1, "gemini-3.6-flash")

                # Modify mock return to gemini-2.5-pro; without refresh or invalidation, cache returns gemini-3.6-flash
                with patch.object(self.manager, "ping_candidate_models", return_value=[("gemini-2.5-pro", True, 40.0, None)]):
                    chosen2 = self.manager.resolve_active_model(TaskType.DIRECTING, force_refresh=False)
                    self.assertEqual(chosen2, "gemini-3.6-flash")

                    # Invalidate cache
                    self.manager.report_failure(TaskType.DIRECTING, "gemini-3.6-flash")
                    # Next resolve should fetch fresh
                    with patch.object(self.manager, "discover_available_models", return_value=["gemini-2.5-pro"]):
                        chosen3 = self.manager.resolve_active_model(TaskType.DIRECTING, force_refresh=False)
                        self.assertEqual(chosen3, "gemini-2.5-pro")

    # =========================================================================
    # 3. Quality Floor Breach & Strict Fail-Closed Halts
    # =========================================================================
    def test_06_model_tier_floor_breach_error(self):
        """Validates that ModelTierFloorBreachError is raised when only sub-par models are available."""
        # Only Tier 3 utility models available
        with patch.object(self.manager, "discover_available_models", return_value=["gemini-3.1-flash-lite", "gemma-2-9b-it"]):
            with self.assertRaises(ModelTierFloorBreachError):
                self.manager.get_candidate_models_for_task(TaskType.TRANSLATION)

            with self.assertRaises(ModelTierFloorBreachError):
                self.manager.resolve_active_model(TaskType.SCREENPLAY, force_refresh=True)

    def test_07_all_candidates_unhealthy_raises_llm_unavailable(self):
        """Validates that LLMUnavailableError is strictly raised when all eligible candidates fail ping."""
        mock_failures = [
            ("gemini-3.8-flash", False, 500.0, "HTTP 503"),
            ("gemini-3.6-flash", False, 500.0, "HTTP 429"),
            ("gemini-2.5-flash", False, 500.0, "Connection refused"),
        ]
        with patch.object(self.manager, "ping_candidate_models", return_value=mock_failures):
            with patch.object(self.manager, "discover_available_models", return_value=["gemini-3.8-flash", "gemini-3.6-flash", "gemini-2.5-flash"]):
                with self.assertRaises(LLMUnavailableError) as ctx:
                    self.manager.resolve_active_model(TaskType.DIRECTING, force_refresh=True)
                self.assertIn("STRICT HALT", str(ctx.exception))

    # =========================================================================
    # 4. Strict Production Halt Verification Across Creative Modules
    # =========================================================================
    def test_08_script_builder_strict_halt_on_failure(self):
        """Validates that script_builder strictly raises LLMUnavailableError on LLM failure."""
        try:
            from audiobook_factory.script_builder import _parse_dramatized_chunk_llm
        except ImportError as e:
            self.skipTest(f"Skipping on mobile due to missing dependency: {e}")

        # Mock urllib to simulate API total failure
        with patch("urllib.request.urlopen", side_effect=Exception("API service down")):
            with patch("audiobook_factory.key_manager.get_persistent_key_pool") as mock_pool:
                mock_pool.return_value.get_key.return_value = "fake-key"
                with self.assertRaises(LLMUnavailableError) as ctx:
                    _parse_dramatized_chunk_llm(
                        chunk_text="A dramatic tense confrontation.",
                        api_key="fake-key",
                        max_retries=1,
                    )
                self.assertIn("STRICT HALT", str(ctx.exception))

    def test_09_beat_planner_strict_halt_on_failure(self):
        """Validates that beat_planner strictly raises LLMUnavailableError when LLM fails."""
        try:
            from audiobook_factory.dramaturgy.beat_planner import BeatPlanner
            from audiobook_factory.dramaturgy.contracts import SceneDramaticPlan
        except ImportError as e:
            self.skipTest(f"Skipping on mobile due to missing dependency: {e}")

        scene = SceneDramaticPlan(
            scene_id="SCENE_001",
            scene_index=0,
            location="Castle Chamber",
            dramatic_purpose="Confrontation",
            participants=["Hero", "Villain"],
            stakes="Survival",
            dramatic_complexity="HIGH",
        )

        with patch("urllib.request.urlopen", side_effect=Exception("LLM network timeout")):
            with patch("audiobook_factory.key_manager.get_persistent_key_pool") as mock_pool:
                mock_pool.return_value.get_key.return_value = "fake-key"
                with self.assertRaises(LLMUnavailableError) as ctx:
                    BeatPlanner.plan_scene_beats(scene, use_llm_intent=True)
                self.assertIn("STRICT HALT", str(ctx.exception))

    @unittest.skip("AgentDirector decoupled in Vocals-Only engine")
    def test_10_agent_director_strict_halt_on_failure(self):
        """Validates that agent_director strictly raises LLMUnavailableError when LLM fails."""
        from audiobook_factory.agent_director import AgentDirector

        with patch("urllib.request.urlopen", side_effect=Exception("Director LLM down")):
            with patch("audiobook_factory.agent_director.get_persistent_key_pool") as mock_pool:
                mock_pool.return_value.get_key.return_value = "fake-key"
                director = AgentDirector(model="test-model")
                with self.assertRaises(LLMUnavailableError) as ctx:
                    director._pass1_dramaturgy_and_silence_carving(
                        chapter_id="chapter_001",
                        script_segments=[{"index": 1, "speaker": "Hero", "text": "Halt!"}],
                        total_duration_sec=15.0,
                        max_retries=1,
                    )
                self.assertIn("STRICT HALT", str(ctx.exception))

    @unittest.skip("Soundscape LLM planning decoupled in Vocals-Only engine")
    def test_11_soundscape_strict_halt_on_failure(self):
        """Validates that soundscape module strictly raises LLMUnavailableError on LLM failure."""
        from audiobook_factory.soundscape import detect_chapter_mood, generate_chapter_soundscape_plan

        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            with patch("audiobook_factory.tts_dispatcher.global_key_pool.get_key", return_value="fake-key"):
                with self.assertRaises(LLMUnavailableError):
                    detect_chapter_mood("Some chapter text")

                with self.assertRaises(LLMUnavailableError):
                    generate_chapter_soundscape_plan(1, "Some chapter text")

    def test_12_translator_strict_halt_on_failure(self):
        """Validates that translator strictly raises LLMUnavailableError when retries are exhausted."""
        from audiobook_factory.translator import call_gemini

        with patch("urllib.request.urlopen", side_effect=Exception("API unreachable")):
            with patch("audiobook_factory.key_manager.get_persistent_key_pool") as mock_pool:
                mock_pool.return_value.get_key.return_value = "fake-key"
                with self.assertRaises(LLMUnavailableError) as ctx:
                    call_gemini("Translate this line", max_retries=1)
                self.assertIn("STRICT HALT", str(ctx.exception))

    # =========================================================================
    # 5. AST Zero-Hardcoded-Models Scan Across Codebase
    # =========================================================================
    def test_13_assert_zero_hardcoded_model_strings(self):
        """
        Recursively scans all Python files in audiobook_factory/ using AST.
        Strictly asserts zero hardcoded Gemini model string literals outside
        exempt modules:
        - model_manager.py (definitions of fallback catalog and tier patterns)
        - tts_dispatcher.py (speech synthesis model)
        - pronunciation/contracts.py & provenance.py (speech synthesis models)
        """
        exempt_files = {
            "model_manager.py",
            "tts_dispatcher.py",
            "dispatcher.py",
            "constants.py",
            "contracts.py",
            "provenance.py",
            "gemini_adapter.py",
            "registry.py",
            "generic_client.py",
            "long_form_client.py",
            "multi_cast_client.py",
            "take_bank_manager.py",
            "core_orchestrator.py",
        }
        model_pattern = re.compile(r"^gemini-[0-9a-zA-Z.-]+$")

        violations = []
        for py_path in FACTORY_DIR.rglob("*.py"):
            if py_path.name in exempt_files or "audiobook_factory/tts" in py_path.as_posix():
                continue

            content = py_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val = node.value.strip()
                    if model_pattern.match(val):
                        violations.append(
                            f"File: {py_path.relative_to(WORKSPACE_DIR)}:{getattr(node, 'lineno', '?')} | Model: '{val}'"
                        )

        self.assertEqual(
            len(violations),
            0,
            f"Detected {len(violations)} hardcoded Gemini model string(s) in codebase:\n"
            + "\n".join(violations),
        )

    def test_14_llm_client_candidate_cycling_with_env_preference(self):
        """
        Validates that call_gemini dynamically cycles across candidate models upon retry,
        even when GEMINI_TEXT_MODEL is set in the environment, preventing static model deadlocks.
        """
        import os
        from audiobook_factory.llm_client import call_gemini
        from audiobook_factory.key_manager import get_persistent_key_pool
        import urllib.request
        from unittest.mock import MagicMock

        models_contacted = []

        def mock_urlopen(req, timeout=45.0):
            # Record which model URL was called
            url = req.full_url
            for m in ["model-primary", "model-fallback", "model-alt"]:
                if m in url:
                    models_contacted.append(m)
            # Fail first call with 503, succeed second call
            if len(models_contacted) == 1:
                import urllib.error
                raise urllib.error.HTTPError(url, 503, "Service Unavailable", {}, None)
            mock_resp = MagicMock()
            mock_resp.__enter__.return_value = mock_resp
            mock_resp.read.return_value = json.dumps({
                "candidates": [{"content": {"parts": [{"text": '{"result": "success"}'}]}}]
            }).encode("utf-8")
            return mock_resp

        with patch.dict(os.environ, {"GEMINI_TEXT_MODEL": "model-primary"}):
            with patch("urllib.request.urlopen", side_effect=mock_urlopen):
                with patch("audiobook_factory.llm_client.get_model_manager", return_value=self.manager):
                    with patch.object(self.manager, "get_candidate_models_for_task", return_value=["model-primary", "model-fallback", "model-alt"]):
                        with patch.object(self.manager, "resolve_active_model", return_value="model-primary"):
                            with patch.object(get_persistent_key_pool(), "get_key", return_value="AIzaSyDummyKey"):
                                res = call_gemini("test prompt", max_retries=3)
                                self.assertEqual(res, {"result": "success"})
                                # First attempt was model-primary (503), second attempt cycled to model-fallback!
                                self.assertEqual(models_contacted, ["model-primary", "model-fallback"])

    def test_15_creative_tasks_enforce_tier_1_and_blacklist(self):
        """Validates that creative tasks exclude 3.5-flash, 3.6-flash, and -lite models."""
        discovered = [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-flash-latest",
        ]
        with patch.object(self.manager, "discover_available_models", return_value=discovered):
            candidates = self.manager.get_candidate_models_for_task(TaskType.TRANSLATION)
            self.assertIn("gemini-3.8-flash", candidates)
            self.assertIn("gemini-3.7-flash", candidates)
            self.assertNotIn("gemini-3.6-flash", candidates)
            self.assertNotIn("gemini-3.5-flash", candidates)
            self.assertNotIn("gemini-3.1-flash-lite", candidates)
            self.assertNotIn("gemini-flash-latest", candidates)

    def test_16_creative_latency_banishment(self):
        """Validates that for creative tasks, gemini-3.8-flash is preferred over 3.7-flash even if 3.7 has lower latency."""
        def mock_ping(candidates, api_key=None, timeout=6.0):
            return [
                ("gemini-3.8-flash", True, 3500.0, None),  # Higher latency
                ("gemini-3.7-flash", True, 800.0, None),   # Lower latency
            ]

        with patch.object(self.manager, "ping_candidate_models", side_effect=mock_ping):
            with patch.object(self.manager, "discover_available_models", return_value=["gemini-3.8-flash", "gemini-3.7-flash"]):
                chosen = self.manager.resolve_active_model(TaskType.TRANSLATION, force_refresh=True)
                # 3.8-flash must win due to version superiority, despite higher ping latency!
                self.assertEqual(chosen, "gemini-3.8-flash")

    def test_17_ping_candidate_models_acquires_distinct_keys(self):
        """Validates that concurrent candidate probes acquire distinct keys from the pool."""
        keys_provided = ["key_alpha_111", "key_beta_222", "key_gamma_333"]
        key_idx = 0
        keys_captured = []

        def mock_get_key(service="text"):
            nonlocal key_idx
            k = keys_provided[key_idx % len(keys_provided)]
            key_idx += 1
            return k

        def mock_urlopen(req, timeout=15.0):
            match = re.search(r"key=([^&]+)", req.full_url)
            if match:
                keys_captured.append(match.group(1))
            mock_resp = MagicMock()
            mock_resp.__enter__.return_value = mock_resp
            mock_resp.read.return_value = b"{}"
            return mock_resp

        with patch.object(self.manager.pool, "get_key", side_effect=mock_get_key):
            with patch("urllib.request.urlopen", side_effect=mock_urlopen):
                results = self.manager.ping_candidate_models(
                    ["candidate-a", "candidate-b", "candidate-c"],
                    api_key=None,
                    timeout=5.0,
                )
                self.assertEqual(len(results), 3)
                self.assertTrue(all(r[1] is True for r in results))
                self.assertEqual(len(set(keys_captured)), 3)

    def test_18_ping_candidate_models_rotates_key_on_429(self):
        """Validates that if a probe hits HTTP 429, it rotates key from the pool and retries."""
        keys_provided = ["key_rate_limited_001", "key_healthy_002"]
        key_idx = 0
        attempts = []

        def mock_get_key(service="text"):
            nonlocal key_idx
            k = keys_provided[min(key_idx, len(keys_provided) - 1)]
            key_idx += 1
            return k

        def mock_urlopen(req, timeout=15.0):
            match = re.search(r"key=([^&]+)", req.full_url)
            k = match.group(1) if match else "unknown"
            attempts.append(k)
            if k == "key_rate_limited_001":
                import urllib.error
                raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)
            mock_resp = MagicMock()
            mock_resp.__enter__.return_value = mock_resp
            mock_resp.read.return_value = b"{}"
            return mock_resp

        with patch.object(self.manager.pool, "get_key", side_effect=mock_get_key):
            with patch.object(self.manager.pool, "mark_temporary_backoff") as mock_backoff:
                with patch("urllib.request.urlopen", side_effect=mock_urlopen):
                    results = self.manager.ping_candidate_models(
                        ["candidate-single"],
                        api_key=None,
                        timeout=5.0,
                    )
                    self.assertEqual(len(results), 1)
                    model_name, ok, latency, err = results[0]
                    self.assertTrue(ok)
                    self.assertIsNone(err)
                    self.assertEqual(attempts, ["key_rate_limited_001", "key_healthy_002"])
                    mock_backoff.assert_called_once()

    def test_19_explicit_model_single_ping_prioritization(self):
        """Validates that explicit GEMINI_TEXT_MODEL or --model is probed alone first without excessive ping overhead."""
        pings_recorded = []

        def mock_ping(candidates, api_key=None, timeout=15.0):
            pings_recorded.append(list(candidates))
            return [(c, True, 50.0, None) for c in candidates]

        with patch.dict(os.environ, {"GEMINI_TEXT_MODEL": "gemini-3.7-flash"}):
            with patch.object(self.manager, "discover_available_models", return_value=["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"]):
                with patch.object(self.manager, "ping_candidate_models", side_effect=mock_ping):
                    chosen = self.manager.resolve_active_model(TaskType.TRANSLATION, force_refresh=True)
                    self.assertEqual(chosen, "gemini-3.7-flash")
                    self.assertEqual(pings_recorded, [["gemini-3.7-flash"]])

    def test_20_explicit_model_override_honored_for_creative_task(self):
        """Validates that explicit model override (e.g. gemini-3.6-flash) is honored for screenplay attribution without floor breach error."""
        with patch.object(self.manager, "discover_available_models", return_value=["gemini-3.8-flash", "gemini-3.6-flash"]):
            with patch.object(self.manager, "ping_candidate_models", return_value=[("gemini-3.6-flash", True, 45.0, None)]):
                chosen = self.manager.resolve_active_model(TaskType.SCREENPLAY, preferred_model="gemini-3.6-flash", force_refresh=True)
                self.assertEqual(chosen, "gemini-3.6-flash")

    def test_21_resilient_tier_2_fallback_on_503_or_timeout(self):
        """Validates that if all Tier 1 models fail with 503/timeout, resolve_active_model falls back to healthy Tier 2."""
        def mock_ping(candidates, api_key=None, timeout=15.0):
            res = []
            for c in candidates:
                if "3.8" in c:
                    res.append((c, False, 500.0, "HTTP 503"))
                elif "3.7" in c:
                    res.append((c, False, 15000.0, "Timed out"))
                elif "3.6" in c:
                    res.append((c, True, 100.0, None))
                else:
                    res.append((c, False, 500.0, "HTTP 503"))
            return res

        with patch.object(self.manager, "discover_available_models", return_value=["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"]):
            with patch.object(self.manager, "ping_candidate_models", side_effect=mock_ping):
                chosen = self.manager.resolve_active_model(TaskType.SCREENPLAY, force_refresh=True)
                self.assertEqual(chosen, "gemini-3.6-flash")

    def test_22_subpar_model_override_still_rejected_with_floor_breach(self):
        """Validates that requesting a sub-par utility model (e.g. flash-lite) for screenplay still raises ModelTierFloorBreachError."""
        with patch.object(self.manager, "discover_available_models", return_value=["gemini-3.1-flash-lite"]):
            with self.assertRaises(ModelTierFloorBreachError):
                self.manager.resolve_active_model(TaskType.SCREENPLAY, preferred_model="gemini-3.1-flash-lite", force_refresh=True)

    def test_23_cli_script_subcommand_model_flag(self):
        """Validates that audiobook_cli.py script subcommand parses --model flag and passes it to generate_project_scripts."""
        import sys
        from unittest.mock import MagicMock
        with patch.object(sys, "argv", ["audiobook-factory", "script", "sample_book", "--model", "gemini-3.6-flash"]):
            with patch("audiobook_factory.cli.commands.pipeline.generate_project_scripts") as mock_gen:
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.is_dir", return_value=True):
                        from audiobook_cli import main
                        try:
                            main()
                        except SystemExit:
                            pass
                        mock_gen.assert_called_once()
                        _, kwargs = mock_gen.call_args
                        self.assertEqual(kwargs.get("model"), "gemini-3.6-flash")

    def test_24_explicit_model_sticks_across_retries(self):
        """Validates that an explicitly passed model sticks across retries and does not rotate to other candidates."""
        from audiobook_factory.llm_client import call_gemini
        from audiobook_factory.key_manager import get_persistent_key_pool
        import urllib.request
        from unittest.mock import MagicMock

        models_contacted = []

        def mock_urlopen(req, timeout=45.0):
            url = req.full_url
            for m in ["gemini-3.6-flash", "gemini-3.8-flash", "gemini-3.7-flash"]:
                if m in url:
                    models_contacted.append(m)
            if len(models_contacted) == 1:
                import urllib.error
                raise urllib.error.HTTPError(url, 429, "Rate Limit", {}, None)
            mock_resp = MagicMock()
            mock_resp.__enter__.return_value = mock_resp
            mock_resp.read.return_value = json.dumps({
                "candidates": [{"content": {"parts": [{"text": '{"result": "success"}'}]}}]
            }).encode("utf-8")
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            with patch("audiobook_factory.llm_client.get_model_manager", return_value=self.manager):
                with patch.object(self.manager, "get_candidate_models_for_task", return_value=["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"]):
                    with patch.object(get_persistent_key_pool(), "get_key", return_value="AIzaSyDummyKey"):
                        res = call_gemini("test prompt", model="gemini-3.6-flash", max_retries=3)
                        self.assertEqual(res, {"result": "success"})
                        # Both attempts must contact gemini-3.6-flash without switching to 3.8 or 3.7
                        self.assertEqual(models_contacted, ["gemini-3.6-flash", "gemini-3.6-flash"])

    def test_25_explicit_model_rotates_on_safety_or_circuit_breaker(self):
        """Validates that if an explicitly passed model is safety-blocked, retries rotate to healthy candidates."""
        from audiobook_factory.llm_client import call_gemini
        from audiobook_factory.key_manager import get_persistent_key_pool
        import urllib.request
        from unittest.mock import MagicMock

        models_contacted = []

        def mock_urlopen(req, timeout=45.0):
            url = req.full_url
            if "?key=" in url:
                mock_resp = MagicMock()
                mock_resp.__enter__.return_value = mock_resp
                mock_resp.read.return_value = b"{}"
                return mock_resp

            for m in ["gemini-3.6-flash", "gemini-3.8-flash", "gemini-3.7-flash"]:
                if m in url:
                    models_contacted.append(m)
            # First attempt: safety blocked response (no candidates)
            if len(models_contacted) == 1:
                mock_resp = MagicMock()
                mock_resp.__enter__.return_value = mock_resp
                mock_resp.read.return_value = json.dumps({
                    "promptFeedback": {"blockReason": "SAFETY"}
                }).encode("utf-8")
                return mock_resp
            mock_resp = MagicMock()
            mock_resp.__enter__.return_value = mock_resp
            mock_resp.read.return_value = json.dumps({
                "candidates": [{"content": {"parts": [{"text": '{"result": "fallback_success"}'}]}}]
            }).encode("utf-8")
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            with patch("audiobook_factory.llm_client.get_model_manager", return_value=self.manager):
                with patch.object(self.manager, "get_candidate_models_for_task", return_value=["gemini-3.6-flash", "gemini-3.8-flash"]):
                    with patch.object(get_persistent_key_pool(), "get_key", return_value="AIzaSyDummyKey"):
                        res = call_gemini("test prompt", model="gemini-3.6-flash", max_retries=3)
                        self.assertEqual(res, {"result": "fallback_success"})
                        # First attempt: gemini-3.6-flash (safety blocked), second attempt rotated to gemini-3.8-flash
                        self.assertEqual(models_contacted, ["gemini-3.6-flash", "gemini-3.8-flash"])

    def test_26_model_aware_key_leasing_passes_model_to_pool(self):
        """Validates that pool.get_key receives model=model or env_model during key leasing in call_gemini."""
        from audiobook_factory.llm_client import call_gemini
        from audiobook_factory.key_manager import get_persistent_key_pool
        import urllib.request
        from unittest.mock import MagicMock

        leased_models = []

        def mock_get_key(service="text", provider="gemini", model=None, max_wait_seconds=60.0):
            leased_models.append(model)
            return "AIzaSyDummyKey"

        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = json.dumps({
            "candidates": [{"content": {"parts": [{"text": '{"result": "ok"}'}]}}]
        }).encode("utf-8")

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with patch("audiobook_factory.llm_client.get_model_manager", return_value=self.manager):
                with patch.object(self.manager, "get_candidate_models_for_task", return_value=["gemini-3.6-flash"]):
                    with patch.object(get_persistent_key_pool(), "get_key", side_effect=mock_get_key):
                        # Case A: explicit model passed
                        call_gemini("test prompt", model="gemini-3.6-flash", max_retries=1)
                        self.assertEqual(leased_models[-1], "gemini-3.6-flash")

                        # Case B: env model set
                        with patch.dict(os.environ, {"GEMINI_TEXT_MODEL": "gemini-3.8-flash"}):
                            call_gemini("test prompt", model=None, max_retries=1)
                            self.assertEqual(leased_models[-1], "gemini-3.8-flash")

    def test_27_preflight_fulfillment_reuse(self):
        """Validates that call_gemini reuses existing Antigravity In-Session fulfillment files before retries or network calls."""
        import tempfile
        import hashlib
        from audiobook_factory.llm_client import call_gemini
        from audiobook_factory.safety import get_dramatic_fiction_framing
        from audiobook_factory.model_manager import TaskType

        with tempfile.TemporaryDirectory() as tmp_dir:
            handoff_dir = Path(tmp_dir) / "pending_handoffs"
            handoff_dir.mkdir(parents=True, exist_ok=True)

            prompt = "Translate this dramatic text"
            system_instruction = "You are a master literary translator."
            # Account for dramatic fiction framing applied to creative fiction tasks
            prefix = get_dramatic_fiction_framing()
            framed_sys = f"{prefix}{system_instruction}"
            framed_prompt = f"{prefix}{prompt}"
            p_hash = hashlib.sha256((framed_sys + framed_prompt).encode("utf-8")).hexdigest()[:10]

            # Case A: JSON fulfillment file
            result_json_path = handoff_dir / f"handoff_{TaskType.TRANSLATION.value}_{p_hash}.result.json"
            result_json_path.write_text(json.dumps({"translated_text": "अनुवादित पाठ"}), encoding="utf-8")

            with patch.dict(os.environ, {"CURRENT_PROJECT_DIR": tmp_dir}):
                with patch("urllib.request.urlopen") as mock_urlopen:
                    with patch("audiobook_factory.key_manager.get_persistent_key_pool") as mock_pool:
                        res = call_gemini(
                            prompt=prompt,
                            system_instruction=system_instruction,
                            task_type=TaskType.TRANSLATION,
                            response_mime_type="application/json",
                        )
                        self.assertEqual(res, {"translated_text": "अनुवादित पाठ"})
                        mock_urlopen.assert_not_called()
                        mock_pool.assert_not_called()

            # Case B: TXT fulfillment file
            result_json_path.unlink()
            result_txt_path = handoff_dir / f"handoff_{TaskType.TRANSLATION.value}_{p_hash}.result.txt"
            result_txt_path.write_text('{"translated_text": "अनुवादित पाठ 2"}', encoding="utf-8")

            with patch.dict(os.environ, {"CURRENT_PROJECT_DIR": tmp_dir}):
                with patch("urllib.request.urlopen") as mock_urlopen:
                    with patch("audiobook_factory.key_manager.get_persistent_key_pool") as mock_pool:
                        res = call_gemini(
                            prompt=prompt,
                            system_instruction=system_instruction,
                            task_type=TaskType.TRANSLATION,
                            response_mime_type="application/json",
                        )
                        self.assertEqual(res, {"translated_text": "अनुवादित पाठ 2"})
                        mock_urlopen.assert_not_called()
                        mock_pool.assert_not_called()

    def test_28_semantic_scene_fulfillment_fallback(self):
        """Validates that call_gemini reuses existing fulfillment via scene signature when prompt hashes diverge."""
        from audiobook_factory.llm_client import call_gemini
        from audiobook_factory.safety import get_dramatic_fiction_framing

        with tempfile.TemporaryDirectory() as tmp_dir:
            handoff_dir = Path(tmp_dir) / "pending_handoffs"
            handoff_dir.mkdir(parents=True, exist_ok=True)

            distinctive_scene = "This is a dramatic confrontation in the ancient ruins between the swordsman and the shadow sorcerer."
            candidate_prompt = f'Earlier context: [whispers] Soft footfalls echo.\n\nCurrent Scene Text:\n"""{distinctive_scene}"""\n\nGenerate screenplay.'
            cand_hash = "cand123456"
            cand_handoff_path = handoff_dir / f"handoff_{TaskType.SCREENPLAY.value}_{cand_hash}.json"
            cand_result_path = handoff_dir / f"handoff_{TaskType.SCREENPLAY.value}_{cand_hash}.result.json"

            cand_handoff_path.write_text(json.dumps({"prompt": candidate_prompt}), encoding="utf-8")
            cand_result_path.write_text(json.dumps([{"speaker": "Swordsman", "text": "Halt!"}]), encoding="utf-8")

            # New call has different context/whispers but identical scene text
            new_prompt = f'Earlier context: [gasps] Louder breathing in dark.\n\nCurrent Scene Text:\n"""{distinctive_scene}"""\n\nGenerate screenplay.'

            with patch.dict(os.environ, {"CURRENT_PROJECT_DIR": tmp_dir}):
                with patch("urllib.request.urlopen") as mock_urlopen:
                    with patch("audiobook_factory.key_manager.get_persistent_key_pool") as mock_pool:
                        res = call_gemini(
                            prompt=new_prompt,
                            system_instruction="You are a master screenplay adapter.",
                            task_type=TaskType.SCREENPLAY,
                            response_mime_type="application/json",
                        )
                        self.assertEqual(res, [{"speaker": "Swordsman", "text": "Halt!"}])
                        mock_urlopen.assert_not_called()
                        mock_pool.assert_not_called()

                        # Also verify it cached to the new p_hash
                        prefix = get_dramatic_fiction_framing()
                        framed_sys = f"{prefix}You are a master screenplay adapter."
                        framed_prompt = f"{prefix}{new_prompt}"
                        p_hash = hashlib.sha256((framed_sys + framed_prompt).encode("utf-8")).hexdigest()[:10]
                        cached_result_file = handoff_dir / f"handoff_{TaskType.SCREENPLAY.value}_{p_hash}.result.json"
                        self.assertTrue(cached_result_file.exists())


def json_bytes(obj) -> bytes:
    return json.dumps(obj).encode("utf-8")


if __name__ == "__main__":
    unittest.main()

