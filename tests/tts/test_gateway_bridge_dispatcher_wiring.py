#!/usr/bin/env python3
"""
Unit tests for TTS Gateway Bridge and Legacy Dispatcher Wiring.
Verifies that:
1. execute_tts_to_file writes valid WAV audio through ModelGateway.
2. execute_multispeaker_batch_to_file constructs multi-speaker duo batches.
3. dispatcher._call_gemini_tts and _call_gemini_multispeaker_batch route through
   gateway_bridge when unpatched, and honor test mocks when monkeypatched.
4. Offline mock fallback survives API/network errors when mock keys are active.
"""

import os
import wave
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from audiobook_factory.contracts import BatchPlanItem, ScreenplaySegment
from audiobook_factory.core.models.adapters.base import SpeechResult
from audiobook_factory.tts.gateway_bridge import (
    execute_tts_to_file,
    execute_multispeaker_batch_to_file,
    execute_tts_synthesize,
)
from audiobook_factory.tts.dispatcher import (
    _call_gemini_tts,
    _call_gemini_multispeaker_batch,
)


def _create_synthetic_wav_bytes(dur_sec: float = 0.5, sample_rate: int = 24000) -> bytes:
    """Generates valid WAV bytes for testing."""
    import io, struct
    num_samples = int(sample_rate * dur_sec)
    samples = [6000 if (i // 40) % 2 == 0 else -6000 for i in range(num_samples)]
    pcm = struct.pack(f"<{num_samples}h", *samples)
    with io.BytesIO() as buf:
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm)
        return buf.getvalue()


def test_execute_tts_to_file_writes_wav(tmp_path):
    """Verifies that execute_tts_to_file produces a valid WAV file with correct duration."""
    out_file = tmp_path / "single_test.wav"
    wav_bytes = _create_synthetic_wav_bytes(dur_sec=0.6)
    mock_res = SpeechResult(
        audio_bytes=wav_bytes,
        mime_type="audio/wav",
        sample_rate=24000,
        duration_sec=0.6,
        tokens_used=12,
        model_id="gemini-3.8-flash",
        provider="gemini",
    )

    with patch("audiobook_factory.tts.gateway_bridge.execute_tts_synthesize", return_value=mock_res) as mock_syn:
        path, dur = execute_tts_to_file(
            text="यह एक परीक्षण संवाद है।",
            output_file=out_file,
            voice="Puck",
            speaker="Narrator",
        )
        assert path.exists()
        assert path.stat().st_size > 44
        assert dur == pytest.approx(0.6, rel=0.1)
        mock_syn.assert_called_once()


def test_execute_multispeaker_batch_to_file_writes_wav(tmp_path):
    """Verifies that execute_multispeaker_batch_to_file produces a valid duo batch WAV."""
    out_file = tmp_path / "batch_test.wav"
    wav_bytes = _create_synthetic_wav_bytes(dur_sec=1.2)
    mock_res = SpeechResult(
        audio_bytes=wav_bytes,
        mime_type="audio/wav",
        sample_rate=24000,
        duration_sec=1.2,
        tokens_used=25,
        model_id="gemini-3.8-flash",
        provider="gemini",
    )

    batch = BatchPlanItem(
        batch_id="b_test_01",
        chapter_num=1,
        strategy="multi_speaker_duo",
        speakers=["Geralt", "Yennefer"],
        segments=[
            ScreenplaySegment(index=1, chapter=1, speaker="Geralt", text="नमस्ते"),
            ScreenplaySegment(index=2, chapter=1, speaker="Yennefer", text="स्वागत है"),
        ],
        voice_map={"Geralt": "Fenrir", "Yennefer": "Aoede"},
    )

    with patch("audiobook_factory.tts.gateway_bridge.execute_tts_synthesize", return_value=mock_res) as mock_syn:
        path, dur = execute_multispeaker_batch_to_file(
            batch=batch,
            output_file=out_file,
            voice_map=batch.voice_map,
        )
        assert path.exists()
        assert dur == pytest.approx(1.2, rel=0.1)
        mock_syn.assert_called_once()
        # Verify multiSpeakerVoiceConfig was injected
        call_kwargs = mock_syn.call_args[1]
        assert "speech_config" in call_kwargs
        assert "multiSpeakerVoiceConfig" in call_kwargs["speech_config"]


def test_dispatcher_call_gemini_tts_unpatched_routes_to_gateway(tmp_path):
    """Verifies that unpatched _call_gemini_tts in dispatcher routes through execute_tts_to_file."""
    out_file = tmp_path / "dispatcher_unpatched.wav"
    with patch("audiobook_factory.tts.gateway_bridge.execute_tts_to_file", return_value=(out_file, 0.75)) as mock_bridge:
        path, dur = _call_gemini_tts(
            text="सीधा कंट्रोल प्लेन टेस्ट",
            output_file=out_file,
            voice="Puck",
        )
        assert dur == 0.75
        mock_bridge.assert_called_once()


def test_dispatcher_call_gemini_tts_monkeypatched_honors_mock(tmp_path):
    """Verifies that monkeypatching tts_dispatcher.synthesize_gemini_tts is respected (backward-compat)."""
    out_file = tmp_path / "dispatcher_patched.wav"
    fake_mock = MagicMock(return_value=(out_file, 1.23))

    with patch("audiobook_factory.tts_dispatcher.synthesize_gemini_tts", fake_mock):
        path, dur = _call_gemini_tts(
            text="मंकीपैच टेस्ट",
            output_file=out_file,
            voice="Puck",
        )
        assert dur == 1.23
        fake_mock.assert_called_once()


def test_offline_mock_fallback_robustness():
    """Verifies that when MOCK_OFFLINE=1, any gateway failure triggers the synthetic WAV fallback."""
    os.environ["MOCK_OFFLINE"] = "1"
    try:
        with patch("audiobook_factory.core.models.gateway.get_model_gateway", side_effect=RuntimeError("Simulated API Error")):
            res = execute_tts_synthesize("ऑफ़लाइन मॉक टेस्ट", voice_name="Puck")
            assert res.metadata.get("mock_mode") is True
            assert res.duration_sec == 0.8
            assert len(res.audio_bytes) > 44
    finally:
        os.environ.pop("MOCK_OFFLINE", None)


def test_split_text_into_speech_chunks_basic():
    """Verifies that split_text_into_speech_chunks breaks text into chunks <= max_words."""
    from audiobook_factory.tts.gateway_bridge import split_text_into_speech_chunks
    short_text = "यह एक छोटा वाक्य है।"
    chunks = split_text_into_speech_chunks(short_text, max_words=28)
    assert len(chunks) == 1
    assert chunks[0][0] == short_text
    assert chunks[0][1] == 0.0

    long_text = (
        "मलबे के बीच सिमटे नगरवासी उस टूटे-फूटे खण्डहर में मुँह बाए अंधेरे गर्त को, पत्थरों से घिरे उस स्याह बिल को चुपचाप ताक रहे थे। "
        "पीले वास्कट में खड़ा एक भारी-भरकम एल्डरमैन इस पैर से उस पैर पर झूलता रहा, गला खंकारकर साफ़ किया और अपनी मुड़ी-तुड़ी टोपी उतार ली। "
        "उसने अपनी पतली पड़ चुकी भौंहों से पसीना पोंछते हुए कहा—"
    )
    chunks = split_text_into_speech_chunks(long_text, max_words=28, is_dialogue=False)
    assert len(chunks) == 3
    for chunk_text, pause in chunks:
        assert len(chunk_text.split()) <= 28
    assert chunks[0][1] == 0.35
    assert chunks[1][1] == 0.35
    assert chunks[2][1] == 0.0


def test_execute_tts_to_file_multi_chunk_stitching(tmp_path):
    """Verifies that execute_tts_to_file splits long utterances, calls synthesis per chunk, and concatenates."""
    out_file = tmp_path / "long_stitched.wav"
    wav_bytes = _create_synthetic_wav_bytes(dur_sec=1.0)
    mock_res = SpeechResult(
        audio_bytes=wav_bytes,
        mime_type="audio/wav",
        sample_rate=24000,
        duration_sec=1.0,
        tokens_used=12,
        model_id="gemini-3.8-flash",
        provider="gemini",
    )

    long_text = (
        "मलबे के बीच सिमटे नगरवासी उस टूटे-फूटे खण्डहर में मुँह बाए अंधेरे गर्त को, पत्थरों से घिरे उस स्याह बिल को चुपचाप ताक रहे थे। "
        "पीले वास्कट में खड़ा एक भारी-भरकम एल्डरमैन इस पैर से उस पैर पर झूलता रहा, गला खंकारकर साफ़ किया और अपनी मुड़ी-तुड़ी टोपी उतार ली। "
        "उसने अपनी पतली पड़ चुकी भौंहों से पसीना पोंछते हुए कहा—"
    )

    with patch("audiobook_factory.tts.gateway_bridge.execute_tts_synthesize", return_value=mock_res) as mock_syn:
        path, dur = execute_tts_to_file(
            text=long_text,
            output_file=out_file,
            voice="hi-in-tutor-1",
            speaker="Narrator",
        )
        assert path.exists()
        assert mock_syn.call_count == 3
        # 3 chunks of 1.0s + 2 pauses of 0.35s = ~3.7s
        assert dur > 3.0

