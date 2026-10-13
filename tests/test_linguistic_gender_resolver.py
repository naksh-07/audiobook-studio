#!/usr/bin/env python3
"""
Unit tests for LinguisticGenderResolver.
Verifies English pronoun window analysis, title honorifics, and Hindi verb agreement.
"""

import unittest
from audiobook_factory.preproduction.linguistic_gender_resolver import (
    LinguisticGenderResolver,
    GenderEvidence,
)


class TestLinguisticGenderResolver(unittest.TestCase):

    def test_male_pronoun_window_resolution(self):
        sample = """
        Geralt walked into the tavern. He unbuckled his sword and placed it on the bench.
        "Beer," he said to the barkeep. The man looked at him with suspicious eyes.
        Geralt sat down, resting his tired boots. He knew danger was close.
        """
        ev = LinguisticGenderResolver.resolve_gender("Geralt", sample)
        self.assertEqual(ev.gender, "male")
        self.assertGreater(ev.male_score, ev.female_score)
        self.assertGreaterEqual(ev.confidence, 0.70)

    def test_female_pronoun_window_resolution(self):
        sample = """
        Yennefer raised her hand, sparks dancing on her fingers. She was furious.
        "Do not test me," she whispered. Her violet eyes flashed with ancient power.
        The sorceress turned away, pulling her velvet cloak tight around her shoulders.
        """
        ev = LinguisticGenderResolver.resolve_gender("Yennefer", sample)
        self.assertEqual(ev.gender, "female")
        self.assertGreater(ev.female_score, ev.male_score)
        self.assertGreaterEqual(ev.confidence, 0.70)

    def test_title_honorific_weighting(self):
        # Even with minimal context, male title drives resolution
        sample = "Alderman Herbolth signed the decree without looking up."
        ev = LinguisticGenderResolver.resolve_gender("Herbolth", sample, associated_titles=["Alderman"])
        self.assertEqual(ev.gender, "male")

        # Female title drives resolution
        sample2 = "Duchess Anarietta inspected the guards."
        ev2 = LinguisticGenderResolver.resolve_gender("Anarietta", sample2, associated_titles=["Duchess"])
        self.assertEqual(ev2.gender, "female")

    def test_hindi_verb_agreement_resolution(self):
        sample_hi = """
        कसाई गार ने अपनी छुरी मेज़ पर पटकी। वह गुस्से से बोला, "यहाँ से निकल जाओ!"
        उसने गेराल्ट की ओर देखा और आगे बढ़ा। वह एक भारी-भरकम आदमी था।
        """
        ev = LinguisticGenderResolver.resolve_gender("Gar", sample_hi, aliases=["कसाई गार", "गार"])
        self.assertEqual(ev.gender, "male")

    def test_batch_resolution_eliminates_neutral(self):
        corpus = """
        Dandelion laughed loudly. He strummed his lute and began singing a ballad.
        "Listen to this," he cried to the tavern patrons.

        Ciri ran across the courtyard. She tripped on her dress but quickly regained her footing.
        She was breathing heavily, her face covered in dust.
        """
        cands = [
            {"english_name": "Dandelion", "gender": "neutral"},
            {"english_name": "Ciri", "gender": "neutral"},
            {"english_name": "UnknownExtra", "gender": "neutral"},
        ]
        resolved = LinguisticGenderResolver.resolve_candidates_batch(cands, corpus)
        self.assertEqual(resolved[0]["gender"], "male")
        self.assertEqual(resolved[1]["gender"], "female")
        self.assertEqual(resolved[2]["gender"], "male")  # Fallback default male, never neutral

    def test_alderman_gender_resolution_and_wife_of_phrase(self):
        # 1. Direct title in target_name
        ev = LinguisticGenderResolver.resolve_gender("Alderman", "")
        self.assertEqual(ev.gender, "male")
        self.assertGreater(ev.male_score, 0)

        # 2. "wife of the Alderman" must not turn Alderman female; Alderman is male
        sample = "The wife of the Alderman greeted the guests at the town gate."
        ev_alderman = LinguisticGenderResolver.resolve_gender("Alderman", sample)
        self.assertEqual(ev_alderman.gender, "male")
        self.assertGreaterEqual(ev_alderman.male_score, 35)
        self.assertEqual(ev_alderman.female_score, 0)

        # 3. Target name containing female title resolves female
        ev_queen = LinguisticGenderResolver.resolve_gender("Queen Calanthe", "")
        self.assertEqual(ev_queen.gender, "female")
        self.assertGreater(ev_queen.female_score, 0)


if __name__ == "__main__":
    unittest.main()
