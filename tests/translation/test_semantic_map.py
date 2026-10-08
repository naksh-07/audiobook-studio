#!/usr/bin/env python3
"""
Unit and Integration Tests for Source & Target Semantic Map Engine and Passive-Voice Extraction.
"""

import unittest
from audiobook_factory.translation.source_semantic_map import (
    build_source_semantic_map,
    build_target_semantic_map,
    SemanticAligner,
    _extract_source_action_and_actors,
)


class TestSemanticMap(unittest.TestCase):

    def test_01_passive_voice_semantic_role_alignment(self):
        """
        Verify that passive-voice sentences (X was struck by Y) correctly identify
        Y as the actor/agent and X as the recipient/patient, preventing role inversion.
        """
        known_entities = ["Geralt", "Elena", "Valerius"]

        # Case 1: Passive with named entity recipient and generic role agent
        s1 = "Geralt was struck by the assassin."
        actors1, action1, recips1, _ = _extract_source_action_and_actors(s1, known_entities)
        self.assertIn("the assassin", [a.lower() for a in actors1], f"Expected assassin as actor: {actors1}")
        self.assertIn("Geralt", recips1, f"Expected Geralt as recipient: {recips1}")
        self.assertEqual(action1, "struck")

        # Case 2: Passive with named entity agent and named entity recipient
        s2 = "Elena was healed by Valerius."
        actors2, action2, recips2, _ = _extract_source_action_and_actors(s2, known_entities)
        self.assertIn("Valerius", actors2, f"Expected Valerius as actor: {actors2}")
        self.assertIn("Elena", recips2, f"Expected Elena as recipient: {recips2}")
        self.assertEqual(action2, "healed")

        # Case 3: Active-voice contrast
        s3 = "The assassin struck Geralt with a silver dagger."
        actors3, action3, recips3, objs3 = _extract_source_action_and_actors(s3, known_entities)
        self.assertIn("the assassin", [a.lower() for a in actors3])
        self.assertIn("Geralt", recips3)
        self.assertEqual(action3, "struck")

    def test_02_build_source_semantic_map_with_passive_propositions(self):
        scene_text = """
The courtyard was quiet at midnight.
Geralt was poisoned by the sorceress with wolfsbane.
He collapsed upon the cold stones.
"""
        known_entities = ["Geralt"]
        s_map = build_source_semantic_map(scene_text, scene_id="sc_001", known_entities=known_entities)
        self.assertEqual(s_map.total_beats, 3)

        # Beat 2 is the passive sentence
        b2 = s_map.propositions[1]
        self.assertIn("the sorceress", [a.lower() for a in b2.actors])
        self.assertIn("Geralt", b2.recipients)
        self.assertEqual(b2.action, "poisoned")


if __name__ == "__main__":
    unittest.main()
