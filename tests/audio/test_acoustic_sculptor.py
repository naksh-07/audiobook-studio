#!/usr/bin/env python3
"""
Unit test suite for AcousticContextResolver and DialogueAcousticSculptor (Room 5).
Validates multi-dimensional stem acoustic conditioning across registers and intensities.
"""

import unittest
import numpy as np
from audiobook_factory.audio.contracts import (
    VocalRegister,
    DeliveryIntensity,
    DialogueAcousticContext,
)
from audiobook_factory.audio.dsp import (
    AcousticContextResolver,
    DialogueAcousticSculptor,
    has_pedalboard_engine,
)


class TestAcousticContextResolver(unittest.TestCase):
    """Verifies that AcousticContextResolver correctly maps metadata into acoustic contexts."""

    def test_resolver_soprano_lyrical_aoede(self):
        ctx = AcousticContextResolver.resolve(
            voice_id="Aoede",
            speaker="Narrator",
            gender="female",
            is_narrator=True,
        )
        self.assertEqual(ctx.vocal_register, VocalRegister.SOPRANO_LYRICAL)
        self.assertEqual(ctx.intensity, DeliveryIntensity.CONVERSATIONAL)

    def test_resolver_male_baritone_hero(self):
        ctx = AcousticContextResolver.resolve(
            voice_id="Fenrir",
            speaker="Hero",
            gender="male",
            vocal_traits="deep, authoritative, warm",
        )
        self.assertEqual(ctx.vocal_register, VocalRegister.BARITONE_RESONANT)
        self.assertEqual(ctx.intensity, DeliveryIntensity.CONVERSATIONAL)

    def test_resolver_deep_bass(self):
        ctx = AcousticContextResolver.resolve(
            voice_id="Charon",
            speaker="Giant",
            gender="male",
            vocal_traits="rumbling bass, gravel, heavy",
        )
        self.assertEqual(ctx.vocal_register, VocalRegister.BASS_GRAVEL)

    def test_resolver_tenor_bright(self):
        ctx = AcousticContextResolver.resolve(
            voice_id="Puck",
            speaker="Bard",
            gender="male",
            vocal_traits="young, bright, energetic tenor",
        )
        self.assertEqual(ctx.vocal_register, VocalRegister.TENOR_BRIGHT)

    def test_resolver_elderly_textured(self):
        ctx = AcousticContextResolver.resolve(
            voice_id="Charon",
            speaker="Alderman",
            gender="male",
            character_archetype="elderly weathered town leader",
            age_group="elderly",
        )
        self.assertEqual(ctx.vocal_register, VocalRegister.ELDERLY_TEXTURED)

    def test_resolver_creature_guttural(self):
        ctx = AcousticContextResolver.resolve(
            voice_id="Charon",
            speaker="Beast",
            gender="male",
            character_archetype="monstrous beast",
            vocal_traits="guttural demonic growl",
        )
        self.assertEqual(ctx.vocal_register, VocalRegister.CREATURE_GUTTURAL)

    def test_resolver_explosive_rage(self):
        ctx = AcousticContextResolver.resolve(
            voice_id="Fenrir",
            speaker="Warrior",
            gender="male",
            intensity="explosive",
            emotion="furious rage and combat shout",
        )
        self.assertEqual(ctx.intensity, DeliveryIntensity.EXPLOSIVE_RAGE)

    def test_resolver_whisper_intimate(self):
        ctx = AcousticContextResolver.resolve(
            voice_id="Aoede",
            speaker="Lover",
            gender="female",
            intensity="whisper",
            emotion="tender intimate confession",
        )
        self.assertEqual(ctx.intensity, DeliveryIntensity.WHISPER_INTIMATE)
        self.assertEqual(ctx.vocal_register, VocalRegister.SOPRANO_LYRICAL)

    def test_resolver_subdued_vulnerable(self):
        ctx = AcousticContextResolver.resolve(
            voice_id="Kore",
            speaker="Victim",
            gender="female",
            emotion="weeping in deep grief and sorrow",
        )
        self.assertEqual(ctx.intensity, DeliveryIntensity.SUBDUED_VULNERABLE)


class TestDialogueAcousticSculptor(unittest.TestCase):
    """Verifies in-memory C++ JUCE DSP stem conditioning."""

    def setUp(self):
        self.sr = 24000
        # Generate 1-second synthetic speech test buffer (250Hz + 1kHz + 6kHz tones)
        t = np.linspace(0, 1.0, self.sr, endpoint=False)
        tone = (
            0.3 * np.sin(2 * np.pi * 250.0 * t) +
            0.2 * np.sin(2 * np.pi * 1000.0 * t) +
            0.1 * np.sin(2 * np.pi * 6000.0 * t)
        )
        self.test_pcm = (tone * 32767.0).astype(np.int16).tobytes()

    def test_sculpt_chunk_soprano_lyrical(self):
        # Narrator Transparency Invariant: Narrator Aoede must be 100% bit-for-bit unaltered
        ctx_narrator = DialogueAcousticContext(
            vocal_register=VocalRegister.SOPRANO_LYRICAL,
            intensity=DeliveryIntensity.CONVERSATIONAL,
            voice_id="Aoede",
            speaker="Narrator",
            gender="female",
            is_narrator=True,
            sample_rate=self.sr,
        )
        sculpted_narrator = DialogueAcousticSculptor.sculpt_chunk(self.test_pcm, ctx_narrator, sample_rate=self.sr)
        self.assertEqual(sculpted_narrator, self.test_pcm)

        # Non-narrator female character receives gentle conditioning
        ctx_char = DialogueAcousticContext(
            vocal_register=VocalRegister.SOPRANO_LYRICAL,
            intensity=DeliveryIntensity.CONVERSATIONAL,
            voice_id="Aoede",
            speaker="Princess",
            gender="female",
            is_narrator=False,
            sample_rate=self.sr,
        )
        sculpted_char = DialogueAcousticSculptor.sculpt_chunk(self.test_pcm, ctx_char, sample_rate=self.sr)
        self.assertIsInstance(sculpted_char, bytes)
        self.assertEqual(len(sculpted_char), len(self.test_pcm))

        if has_pedalboard_engine():
            arr_out = np.frombuffer(sculpted_char, dtype=np.int16).astype(np.float32) / 32768.0
            self.assertGreater(np.max(np.abs(arr_out)), 0.05)
            self.assertLessEqual(np.max(np.abs(arr_out)), 1.0)

    def test_sculpt_chunk_baritone_resonant(self):
        ctx = DialogueAcousticContext(
            vocal_register=VocalRegister.BARITONE_RESONANT,
            intensity=DeliveryIntensity.CONVERSATIONAL,
            voice_id="Fenrir",
            speaker="Hero",
            gender="male",
            sample_rate=self.sr,
        )
        sculpted = DialogueAcousticSculptor.sculpt_chunk(self.test_pcm, ctx, sample_rate=self.sr)
        self.assertIsInstance(sculpted, bytes)
        self.assertEqual(len(sculpted), len(self.test_pcm))

    def test_sculpt_chunk_explosive_rage(self):
        ctx = DialogueAcousticContext(
            vocal_register=VocalRegister.BARITONE_RESONANT,
            intensity=DeliveryIntensity.EXPLOSIVE_RAGE,
            voice_id="Fenrir",
            speaker="Hero",
            gender="male",
            sample_rate=self.sr,
        )
        sculpted = DialogueAcousticSculptor.sculpt_chunk(self.test_pcm, ctx, sample_rate=self.sr)
        self.assertIsInstance(sculpted, bytes)

    def test_sculpt_chunk_empty_fallback(self):
        ctx = DialogueAcousticContext()
        self.assertEqual(DialogueAcousticSculptor.sculpt_chunk(b"", ctx), b"")


if __name__ == "__main__":
    unittest.main()
