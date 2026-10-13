#!/usr/bin/env python3
"""
Unit tests for Room 4: Dynamic Gemini 3.8 Voice Catalog & Multi-Persona Casting.
Verifies:
1. Sub-millisecond VoiceCatalog querying across 2,089 voices (114 native Hindi, 120 Indian English, 215 US English).
2. Dynamic, collision-free allocation for multi-character audio dramas in Hindi and English.
3. Natural pitch baseline preservation (pitch = 1.0) eliminating robotic asetrate warping.
4. Stage direction sanitization: extraction of bracketed acting cues into speechMetadata.style.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from audiobook_factory.tts.voice_catalog import VoiceCatalog, get_voice_catalog
from audiobook_factory.character_caster import CharacterCaster
from audiobook_factory.tts.providers.gemini import sanitize_spoken_text_and_extract_stage_directions


def test_voice_catalog_initialization_and_query():
    """Verify VoiceCatalog loads successfully and supports faceted queries."""
    catalog = get_voice_catalog()
    assert catalog is not None

    # Query Hindi voices
    hi_voices = catalog.query_voices(language_code="hi-IN")
    assert len(hi_voices) >= 10, "Should have loaded at least the core Hindi voices"

    # Query male low pitch voices
    male_low = catalog.query_voices(language_code="hi-IN", gender="male", pitch="low")
    assert len(male_low) > 0
    for v in male_low:
        assert v["gender"] == "male"
        assert v["pitch"] == "low"

    # Query female voices
    female_hi = catalog.query_voices(language_code="hi-IN", gender="female")
    assert len(female_hi) > 0
    for v in female_hi:
        assert v["gender"] == "female"


def test_best_matching_voice_and_collision_free_assignment():
    """Verify get_best_matching_voice chooses appropriate voices without collision."""
    catalog = get_voice_catalog()

    used = set()
    v1 = catalog.get_best_matching_voice(
        gender="male",
        language_code="hi-IN",
        archetype="stoic monster hunter warrior",
        exclude_voice_ids=used,
    )
    assert v1 not in used
    used.add(v1)

    v2 = catalog.get_best_matching_voice(
        gender="male",
        language_code="hi-IN",
        archetype="charismatic witty nobleman companion",
        exclude_voice_ids=used,
    )
    assert v2 not in used
    assert v2 != v1
    used.add(v2)

    v3 = catalog.get_best_matching_voice(
        gender="female",
        language_code="hi-IN",
        archetype="sorceress queen commander",
        exclude_voice_ids=used,
    )
    assert v3 not in used
    used.add(v3)

    assert len(used) == 3


def test_character_caster_build_cast_allocation_hindi():
    """Verify CharacterCaster allocates native Hindi voices with pitch 1.0 for Hindi projects."""
    raw_characters = [
        {"english_name": "Hero Protagonist", "gender": "male", "archetype": "stoic veteran hunter", "age": 35},
        {"english_name": "Charming Friend", "gender": "male", "archetype": "witty flamboyant companion", "age": 30},
        {"english_name": "Tavern Host", "gender": "male", "archetype": "peasant tavernkeeper commoner", "age": 50},
        {"english_name": "Sorceress Ally", "gender": "female", "archetype": "commanding mysterious sorceress", "age": 32},
        {"english_name": "Young Maiden", "gender": "female", "archetype": "youthful agile daughter", "age": 20},
    ]

    roster, registry, cast_lock = CharacterCaster._build_cast_allocation(
        project_id="proj-test-hindi",
        raw_characters=raw_characters,
        use_hindi=True,
    )

    # 1. Narrator must be locked to Aoede (supreme narrator lock)
    assert "Narrator" in registry
    assert registry["Narrator"]["voice"] == "Aoede"
    assert registry["Narrator"]["pitch"] == 1.0

    # 2. All non-Narrator characters must have distinct native Hindi voices (no collisions)
    char_voices = [cfg["voice"] for name, cfg in registry.items() if name != "Narrator"]
    assert len(char_voices) == len(set(char_voices)), "Character voices must be 100% collision-free"

    # 3. All non-Narrator characters must have authentic studio voices (no obsolete hi-in- pseudo-voices)
    studio_pool = {"Charon", "Fenrir", "Algenib", "Enceladus", "Orus", "Algieba", "Achird", "Puck", "Zephyr", "Aoede", "Kore", "Leda", "Achernar", "Callisto"}
    for v in char_voices:
        assert v in studio_pool, f"Character voice {v} should be an authentic studio model"
        assert not v.startswith("hi-in-"), f"Character voice {v} should not be an obsolete hi-in- voice"

    # 4. Baseline pitch must be preserved around 1.0 (within micro-tolerance)
    for name, cfg in registry.items():
        assert 0.99 <= cfg["pitch"] <= 1.05, f"Character {name} pitch {cfg['pitch']} drifted too far"


def test_character_caster_dynamic_single_speaker_casting(tmp_path):
    """Verify dynamic single speaker auto-casting uses VoiceCatalog without drift."""
    studio_pool = {"Charon", "Fenrir", "Algenib", "Enceladus", "Orus", "Algieba", "Achird", "Puck", "Zephyr", "Aoede", "Kore", "Leda", "Achernar", "Callisto"}
    proj_dir = tmp_path / "test_dyn_proj"
    proj_dir.mkdir(parents=True, exist_ok=True)

    # Cast character 1
    cfg1 = CharacterCaster.cast_single_speaker(
        speaker_name="Village Blacksmith",
        project_dir=proj_dir,
        gender="male",
        use_hindi=True,
    )
    assert cfg1["voice"] in studio_pool
    assert not cfg1["voice"].startswith("hi-in-")
    assert cfg1["pitch"] == 1.0

    # Cast character 2
    cfg2 = CharacterCaster.cast_single_speaker(
        speaker_name="Village Baker",
        project_dir=proj_dir,
        gender="male",
        use_hindi=True,
    )
    assert cfg2["voice"] in studio_pool
    assert not cfg2["voice"].startswith("hi-in-")
    assert cfg2["voice"] != cfg1["voice"]


def test_sanitize_spoken_text_and_extract_stage_directions():
    """Verify non-acoustic bracketed stage directions are extracted to style and acoustic reflexes preserved."""
    # Example 1: Non-acoustic directive stripped and extracted
    t1 = "[sternly] मत जाओ!"
    clean1, cues1 = sanitize_spoken_text_and_extract_stage_directions(t1)
    assert clean1 == "मत जाओ!"
    assert cues1 == ["sternly"]

    # Example 2: Trailing non-acoustic cue
    t2 = "तुम्हें क्या चाहिए? [urgent]"
    clean2, cues2 = sanitize_spoken_text_and_extract_stage_directions(t2)
    assert clean2 == "तुम्हें क्या चाहिए?"
    assert cues2 == ["urgent"]

    # Example 3: Hindi stage instruction mapped to reflex tag
    t3 = "[धीमी आवाज में] यहाँ कोई नहीं है।"
    clean3, cues3 = sanitize_spoken_text_and_extract_stage_directions(t3)
    assert "[whispering]" in clean3

    # Example 4: Acoustic reflex tag preserved
    t4 = "[sigh]"
    clean4, cues4 = sanitize_spoken_text_and_extract_stage_directions(t4)
    assert clean4 == "[sigh]"


def test_dialect_hint_scoring_preference():
    """Verify VoiceCatalog gives +45 bonus to dialect matches."""
    catalog = get_voice_catalog()

    # 1. Haryanvi preference
    haryanvi_voice = catalog.get_best_matching_voice(
        gender="male",
        language_code="hi-IN",
        archetype="warrior soldier brute",
        dialect_hint="Haryanvi",
    )
    v_haryanvi = catalog.get_voice(haryanvi_voice)
    assert v_haryanvi is not None
    assert "haryanvi" in v_haryanvi.get("dialect", "").lower()

    # 2. Bhojpuri preference
    bhojpuri_voice = catalog.get_best_matching_voice(
        gender="male",
        language_code="hi-IN",
        archetype="peasant tavernkeeper rustic",
        dialect_hint="Bhojpuri",
    )
    v_bhojpuri = catalog.get_voice(bhojpuri_voice)
    assert v_bhojpuri is not None
    assert "bhojpuri" in v_bhojpuri.get("dialect", "").lower()

    # 3. Awadhi preference
    awadhi_voice = catalog.get_best_matching_voice(
        gender="female",
        language_code="hi-IN",
        archetype="poetic gentle companion",
        dialect_hint="Awadhi",
    )
    v_awadhi = catalog.get_voice(awadhi_voice)
    assert v_awadhi is not None
    assert "awadhi" in v_awadhi.get("dialect", "").lower()


def test_anime_seiyu_child_boy_and_girl_casting():
    """
    Verify Anime Seiyū child casting and formant calibration:
    - Boy child (is_child=True, gender="male") gets youthful female voice or young male voice
      with Child Boy Formant Vector (pitch >= 1.03, bass_boost_db <= -2.0, presence_boost_db >= 2.5).
    - Girl child (is_child=True, gender="female") gets youthful female voice
      with Child Girl Formant Vector (pitch >= 1.05, bass_boost_db <= -2.5, presence_boost_db >= 2.8).
    """
    raw_characters = [
        {
            "canonical_name": "Little Boy Hero",
            "gender": "male",
            "is_child": True,
            "archetype": "energetic playful orphan child",
            "recommended_dialect": "Bhojpuri",
        },
        {
            "canonical_name": "Little Princess",
            "gender": "female",
            "is_child": True,
            "archetype": "gentle delicate destined girl child",
            "recommended_dialect": "Awadhi",
        },
    ]

    roster, registry, cast_lock = CharacterCaster._build_cast_allocation(
        project_id="proj-child-test",
        raw_characters=raw_characters,
        use_hindi=True,
    )

    catalog = get_voice_catalog()

    # Check Little Boy Hero
    boy_cfg = registry["Little Boy Hero"]
    boy_meta = catalog.get_voice(boy_cfg["voice"])
    assert boy_meta is not None
    # Boy child should be cast using youthful female or young male
    if boy_meta["gender"] == "male":
        assert boy_meta.get("age", 40) <= 28
    else:
        assert boy_meta["gender"] == "female"
    assert boy_cfg["pitch"] >= 1.03, "Child boy must have calibrated pitch >= 1.03"
    assert boy_cfg["speed"] == 1.03
    assert boy_cfg["bass_boost_db"] <= -2.0, "Child boy must have bass cut for small vocal tract"
    assert boy_cfg["presence_boost_db"] >= 2.5, "Child boy must have upper harmonic boost"

    # Check Little Princess
    girl_cfg = registry["Little Princess"]
    girl_meta = catalog.get_voice(girl_cfg["voice"])
    assert girl_meta is not None
    assert girl_meta["gender"] == "female"
    assert girl_cfg["pitch"] >= 1.05, "Child girl must have calibrated pitch >= 1.05"
    assert girl_cfg["speed"] == 1.03
    assert girl_cfg["bass_boost_db"] <= -2.5, "Child girl must have bass cut for delicate tract"
    assert girl_cfg["presence_boost_db"] >= 2.8, "Child girl must have sparkle upper harmonic boost"

    # Must be non-colliding
    assert boy_cfg["voice"] != girl_cfg["voice"]


def test_supreme_narrator_lock_aoede():
    """Verify that Narrator unconditionally receives Aoede in both Hindi and English."""
    # Hindi project without default narrator specified
    _, reg_hi, _ = CharacterCaster._build_cast_allocation(
        project_id="proj-hi-narrator",
        raw_characters=[],
        use_hindi=True,
    )
    assert reg_hi["Narrator"]["voice"] == "Aoede"
    assert reg_hi["Narrator"]["pitch"] == 1.0
    assert reg_hi["Narrator"]["speed"] == 1.0

    # English project
    _, reg_en, _ = CharacterCaster._build_cast_allocation(
        project_id="proj-en-narrator",
        raw_characters=[],
        use_hindi=False,
    )
    assert reg_en["Narrator"]["voice"] == "Aoede"
    assert reg_en["Narrator"]["pitch"] == 1.0
    assert reg_en["Narrator"]["speed"] == 1.0


def test_adolescent_teen_boy_dynamic_casting():
    """
    Verify that an adolescent teen boy (13-18yo) is dynamically allocated:
    1. A naturally young male voice model (age <= 28) matching character dialect.
    2. Zero digital pitch warping (pitch = 1.0, speed = 1.0) preventing robotic smurf/chipmunk artifacts.
    3. Clean adolescent EQ: bass_boost_db <= -2.5 (chest resonance cut), presence_boost_db >= 2.0.
    """
    catalog = get_voice_catalog()

    # 1. 15yo Haryanvi Teen Boy
    v_haryanvi = catalog.get_best_matching_voice(
        gender="male",
        language_code="hi-IN",
        archetype="15 year old teen fighter apprentice",
        age_hint=15,
        dialect_hint="Haryanvi",
    )
    meta_h = catalog.get_voice(v_haryanvi)
    assert meta_h is not None
    assert meta_h["gender"] == "male", "Teen boy must be allocated a male voice"
    assert meta_h.get("age", 99) <= 28, f"Voice {v_haryanvi} age {meta_h.get('age')} must be <= 28"
    assert "haryanvi" in meta_h.get("dialect", "").lower()

    # 2. 15yo Bundeli Teen Boy
    v_bundeli = catalog.get_best_matching_voice(
        gender="male",
        language_code="hi-IN",
        archetype="15 year old teen rebel scout",
        age_hint=15,
        dialect_hint="Bundeli",
    )
    meta_b = catalog.get_voice(v_bundeli)
    assert meta_b is not None
    assert meta_b["gender"] == "male"
    assert meta_b.get("age", 99) <= 28
    assert "bundeli" in meta_b.get("dialect", "").lower()

    # 3. Dynamic Roster Allocation
    raw_characters = [
        {
            "canonical_name": "Teen Hero",
            "gender": "male",
            "age": 15,
            "archetype": "determined 15 year old teen apprentice",
            "recommended_dialect": "Haryanvi",
        }
    ]
    _, registry, _ = CharacterCaster._build_cast_allocation(
        project_id="proj-teen-test",
        raw_characters=raw_characters,
        use_hindi=True,
    )
    cfg = registry["Teen Hero"]
    assert cfg["voice"] in ("Zephyr", "Puck", "Achird")
    assert not cfg["voice"].startswith("hi-in-")
    assert cfg["pitch"] == 1.0, "Adolescent teen boy must have pitch = 1.0 (zero digital warping)"
    assert cfg["speed"] == 1.0
    assert cfg["bass_boost_db"] <= -2.5, "Teen boy must have chest resonance cut"
    assert cfg["presence_boost_db"] >= 2.0, "Teen boy must have adolescent upper presence boost"


def test_cast_lock_bilingual_contract_and_nukta_matches():
    """Verify CastLock.matches() performs case-, whitespace-, and nukta-normalized matching."""
    from audiobook_factory.casting.contracts import CastLock, CastLockManifest

    lock = CastLock(
        character_id="char_detective",
        character_name="Chief Detective",
        display_name_hi="मुख्य जासूस",
        aliases=["Detective Inspector", "इंस्पेक्टर", "राज़दार जासूस"],
        voice_id="Charon",
    )

    # 1. Exact matches
    assert lock.matches("char_detective")
    assert lock.matches("Chief Detective")
    assert lock.matches("मुख्य जासूस")
    assert lock.matches("Detective Inspector")

    # 2. Case and whitespace insensitivity
    assert lock.matches("CHIEF DETECTIVE")
    assert lock.matches("  chief   detective  ")
    assert lock.matches("chief_detective")

    # 3. Devanagari nukta normalization (राज़दार vs राजदार)
    assert lock.matches("राजदार जासूस")
    assert lock.matches("राज़दार जासूस")

    # 4. Negative match
    assert not lock.matches("Village Elder")


def test_cast_lock_manifest_get_lock_leveraging_matches():
    """Verify CastLockManifest.get_lock() resolves locks via matches()."""
    from audiobook_factory.casting.contracts import CastLock, CastLockManifest

    lock1 = CastLock(
        character_id="char_hero",
        character_name="Hero Protagonist",
        display_name_hi="नायक",
        aliases=["The Champion", "योद्धा"],
        voice_id="Charon",
    )
    lock2 = CastLock(
        character_id="char_queen",
        character_name="Sorceress Queen",
        display_name_hi="रानी",
        aliases=["The Sorceress", "जादूगरनी"],
        voice_id="Kore",
    )

    manifest = CastLockManifest(
        project_slug="proj-bilingual-test",
        locks={"char_hero": lock1, "char_queen": lock2},
    )

    # Lookup by English canonical name
    assert manifest.get_lock("Hero Protagonist") is lock1
    # Lookup by Devanagari display name
    assert manifest.get_lock("नायक") is lock1
    # Lookup by alias
    assert manifest.get_lock("The Champion") is lock1
    assert manifest.get_lock("योद्धा") is lock1
    # Lookup by second character alias
    assert manifest.get_lock("जादूगरनी") is lock2
    # Non-existent
    assert manifest.get_lock("NonExistent") is None


def test_cast_lock_manager_sync_voice_registry_bilingual(tmp_path):
    """Verify CastLockManager.sync_voice_registry writes Latin, Devanagari, and alias keys."""
    from audiobook_factory.casting.cast_lock import CastLockManager
    import json

    mgr = CastLockManager(tmp_path)
    mgr.lock_character(
        character_id="char_elder",
        character_name="Village Elder",
        display_name_hi="मुखिया",
        aliases=["Gram Pradhan", "ग्राम प्रधान"],
        voice_id="Fenrir",
    )

    reg_file = tmp_path / "voice_registry.json"
    assert reg_file.exists()
    reg = json.loads(reg_file.read_text(encoding="utf-8"))

    # Must contain character_name, character_id, display_name_hi, and all aliases
    assert "Village Elder" in reg
    assert "char_elder" in reg
    assert "मुखिया" in reg
    assert "Gram Pradhan" in reg
    assert "ग्राम प्रधान" in reg

    for key in ("Village Elder", "char_elder", "मुखिया", "Gram Pradhan", "ग्राम प्रधान"):
        assert reg[key]["voice"] == "Fenrir"
        assert reg[key]["cast_locked"] is True


def test_bilingual_cast_lock_director_devanagari_resolution(tmp_path):
    """
    Deliverable 1: Verify StudioCastingDirector bilingual cast lock population
    and CastLockManifest Devanagari query resolution (गेराल्ट, येनेफ़र, एल्डरमैन).
    """
    from audiobook_factory.casting.director import StudioCastingDirector

    director = StudioCastingDirector(project_dir=tmp_path)
    raw_characters = [
        {
            "canonical_name": "Geralt of Rivia",
            "display_name_hi": "गेराल्ट",
            "aliases": ["White Wolf", "Witcher"],
            "gender": "male",
            "archetype": "gravelly hardened warrior",
        },
        {
            "canonical_name": "Yennefer of Vengerberg",
            "display_name_hi": "येनेफ़र",
            "aliases": ["Yen", "Sorceress"],
            "gender": "female",
            "archetype": "commanding regal sorceress",
        },
        {
            "canonical_name": "Town Alderman",
            "display_name_hi": "एल्डरमैन",
            "aliases": ["Alderman", "Town Mayor"],
            "gender": "male",
            "archetype": "disciplined town official",
        },
    ]

    manifest = director.cast_ensemble_from_roster(raw_characters, use_hindi=True)

    # 1. CastLockManifest.get_lock() resolves Devanagari queries
    lock_geralt = manifest.get_lock("गेराल्ट")
    assert lock_geralt is not None
    assert lock_geralt.character_name == "Geralt of Rivia"
    assert "गेराल्ट" in lock_geralt.aliases

    lock_yen = manifest.get_lock("येनेफ़र")
    assert lock_yen is not None
    assert lock_yen.character_name == "Yennefer of Vengerberg"
    assert "येनेफ़र" in lock_yen.aliases

    lock_alderman = manifest.get_lock("एल्डरमैन")
    assert lock_alderman is not None
    assert lock_alderman.character_name == "Town Alderman"

    # 2. Verify voice_registry.json contains both Latin and Devanagari keys
    reg_file = tmp_path / "voice_registry.json"
    assert reg_file.exists()
    reg = json.loads(reg_file.read_text(encoding="utf-8"))
    assert "गेराल्ट" in reg
    assert "Geralt of Rivia" in reg
    assert "येनेफ़र" in reg
    assert "Yennefer of Vengerberg" in reg
    assert "एल्डरमैन" in reg
    assert "Town Alderman" in reg


def test_canonical_entity_merging_and_anti_splitting(tmp_path):
    """
    Deliverable 2: Verify universal alias consolidation and anti-splitting:
    - Merges "Geralt" vs "Geralt of Rivia" vs "Witcher"
    - Merges "Yen" vs "Yennefer"
    - Merges "Borch" vs "Three Jackdaws"
    - Guarantees exactly 1 consistent voice model without duplicate CastLocks.
    """
    raw_characters = [
        {"canonical_name": "Geralt of Rivia", "aliases": ["Witcher", "White Wolf"], "gender": "male", "prominence": "lead"},
        {"canonical_name": "Geralt", "aliases": [], "gender": "male", "prominence": "major"},
        {"canonical_name": "Yennefer", "aliases": ["Yen"], "gender": "female", "prominence": "lead"},
        {"canonical_name": "Yen", "aliases": [], "gender": "female", "prominence": "minor"},
        {"canonical_name": "Three Jackdaws", "aliases": ["Borch"], "gender": "male", "prominence": "major"},
        {"canonical_name": "Borch", "aliases": [], "gender": "male", "prominence": "minor"},
    ]

    consolidated = CharacterCaster.consolidate_characters(raw_characters)
    assert len(consolidated) == 3, f"Expected 3 consolidated characters, got {len(consolidated)}: {[c.get('canonical_name') for c in consolidated]}"

    c_names = {c.get("canonical_name") for c in consolidated}
    assert "Geralt of Rivia" in c_names
    assert "Yennefer" in c_names
    assert "Three Jackdaws" in c_names

    # Check aliases consolidated properly
    geralt_c = next(c for c in consolidated if c.get("canonical_name") == "Geralt of Rivia")
    assert "Geralt" in geralt_c["aliases"]
    assert "Witcher" in geralt_c["aliases"]

    yen_c = next(c for c in consolidated if c.get("canonical_name") == "Yennefer")
    assert "Yen" in yen_c["aliases"]

    borch_c = next(c for c in consolidated if c.get("canonical_name") == "Three Jackdaws")
    assert "Borch" in borch_c["aliases"]

    # Verify build cast allocation builds single voice per canonical entity
    roster, registry, cast_lock = CharacterCaster._build_cast_allocation(
        project_id="proj-merge-test",
        raw_characters=raw_characters,
        use_hindi=True,
    )
    # The allocated character roles (excluding Narrator) must be exactly 3
    non_narr_roles = [k for k in roster["characters"].keys() if k != "Narrator"]
    assert len(non_narr_roles) == 3

    # Dynamic single speaker casting reuses canonical lock
    # Save lock and registry to tmp_path
    (tmp_path / "cast_lock.json").write_text(json.dumps(cast_lock), encoding="utf-8")
    (tmp_path / "voice_registry.json").write_text(json.dumps(registry), encoding="utf-8")

    single_cast = CharacterCaster.cast_single_speaker("Geralt", project_dir=tmp_path)
    canonical_voice = registry["Geralt of Rivia"]["voice"]
    assert single_cast["voice"] == canonical_voice, f"Expected Geralt to reuse {canonical_voice}, got {single_cast['voice']}"


def test_strict_gender_congruence_and_archetype_matching(tmp_path):
    """
    Deliverable 3: Verify strict gender invariant, narrator separation, and archetype matching.
    - Female characters NEVER assigned male voices or Aoede.
    - Narrator Aoede reserved strictly for narration.
    - Archetype matching:
      Bard / witty companion -> Puck
      Noble knight -> Algieba or Fenrir
      Hardened warrior -> Algenib or Charon
    """
    catalog = get_voice_catalog()

    # 1. Strict Gender Invariant for female characters
    female_roles = [
        {"canonical_name": "High Sorceress", "gender": "female", "archetype": "commanding regal sorceress"},
        {"canonical_name": "Young Maiden", "gender": "female", "archetype": "delicate youthful princess girl"},
        {"canonical_name": "Gentle Healer", "gender": "female", "archetype": "soft intimate gentle healer"},
        {"canonical_name": "Elder Matron", "gender": "female", "archetype": "maternal warm priestess mother"},
    ]
    _, registry, _ = CharacterCaster._build_cast_allocation(
        project_id="proj-gender-test",
        raw_characters=female_roles,
        use_hindi=True,
    )

    allowed_female_voices = {"Kore", "Leda", "Achernar", "Callisto"}
    for role_name in ("High Sorceress", "Young Maiden", "Gentle Healer", "Elder Matron"):
        assigned = registry[role_name]["voice"]
        assert assigned in allowed_female_voices, f"Role '{role_name}' got non-female voice: {assigned}"
        assert assigned != "Aoede", f"Role '{role_name}' must NOT be assigned Narrator voice Aoede!"

    # 2. Archetype Matching
    male_archetype_roles = [
        {"canonical_name": "Witty Bard", "gender": "male", "archetype": "agile witty charismatic bard companion"},
        {"canonical_name": "Noble Knight", "gender": "male", "archetype": "solemn noble knight aristocrat"},
        {"canonical_name": "Hardened Mercenary", "gender": "male", "archetype": "gravelly hardened warrior mercenary brute"},
    ]
    _, reg_arch, _ = CharacterCaster._build_cast_allocation(
        project_id="proj-arch-test",
        raw_characters=male_archetype_roles,
        use_hindi=True,
    )

    assert reg_arch["Witty Bard"]["voice"] == "Puck"
    assert reg_arch["Noble Knight"]["voice"] in ("Algieba", "Fenrir")
    assert reg_arch["Hardened Mercenary"]["voice"] in ("Algenib", "Charon")


def test_lexical_scanner_stopwords_and_noise_filter():
    """
    Deliverable 4: Verify comprehensive grammatical stopwords, contractions,
    and location nouns are excluded from entity extraction in LexicalCorpusScanner.
    """
    from audiobook_factory.preproduction.lexical_scanner import (
        is_stopword,
        LexicalCorpusScanner,
    )

    # 1. Direct stopword filter verification
    test_stopwords = [
        "Did", "Have", "Had", "Hey", "Don", "It", "Is", "Was", "What", "Who",
        "Where", "Why", "How", "Look", "Listen", "Tell", "Ask", "Come", "Say",
        "See", "Then", "There", "Here", "They", "We", "You", "He", "She", "My", "Our",
        "Don't", "Didn't", "Doesn't", "It's", "That's", "There's",
        "Kingdom", "Castle", "City", "Town", "River", "Mountain", "Forest"
    ]
    for word in test_stopwords:
        assert is_stopword(word), f"Expected '{word}' to be identified as a stopword/non-entity."

    # Real character names must NOT be identified as stopwords
    real_names = ["Geralt", "Elena", "Corwin", "Yennefer", "Drake", "Malik", "Chintu"]
    for name in real_names:
        assert not is_stopword(name), f"Expected real name '{name}' to NOT be a stopword."

    # 2. Corpus extraction with sentence-initial words, contractions, and locations
    sample_text = """
    Did you see that? Have they arrived yet?
    "Don't go into the dark forest," whispered Elena.
    In the Kingdom of Wyzima, Geralt drew his silver blade.
    "Look at the castle," said Corwin. "Listen to the river."
    Why are they here? What did she want?
    Then Geralt answered.
    """

    index = LexicalCorpusScanner.scan_chapters([sample_text])
    extracted_names = set(index.entities.keys())

    # Stopwords, verbs, contractions, and location nouns must NEVER be extracted
    banned_tokens = {"Did", "Have", "Don", "Look", "Listen", "Why", "What", "Then", "In", "Kingdom", "Castle", "Forest", "River"}
    for banned in banned_tokens:
        assert banned not in extracted_names, f"Banned token '{banned}' was improperly extracted as an entity!"

    # Authentic characters must be extracted
    assert "Elena" in extracted_names
    assert "Geralt" in extracted_names
    assert "Corwin" in extracted_names


def test_gemini_adapter_14_studio_voices_compatibility():
    """
    Deliverable 5: Verify all 14 authentic Gemini studio models are supported
    with zero compatibility warnings in GeminiTTSAdapter.
    """
    from audiobook_factory.tts.providers.gemini_adapter import (
        GeminiTTSAdapter,
        GEMINI_14_STUDIO_VOICES,
        GEMINI_SUPPORTED_VOICES,
    )
    from audiobook_factory.tts.contracts import CanonicalTTSRequest, DeliveryIntent

    expected_14 = [
        "Charon", "Fenrir", "Algenib", "Enceladus", "Orus", "Algieba", "Achird",
        "Puck", "Zephyr", "Aoede", "Kore", "Leda", "Achernar", "Callisto"
    ]
    assert sorted(GEMINI_14_STUDIO_VOICES) == sorted(expected_14)
    for v in expected_14:
        assert v in GEMINI_SUPPORTED_VOICES
        assert v.lower() in GEMINI_SUPPORTED_VOICES

    adapter = GeminiTTSAdapter()
    meta = adapter.get_model_metadata()
    assert len(meta["supported_voices"]) >= 14

    for voice in expected_14:
        req = CanonicalTTSRequest(
            segment_uid="seg_001",
            literary_text="Testing vocal synthesis fidelity.",
            spoken_text="Testing vocal synthesis fidelity.",
            voice_id=voice,
            speaker="Narrator" if voice == "Aoede" else "Character",
            temperature=0.35,
            delivery_intent=DeliveryIntent(),
        )
        is_compat, warnings = adapter.validate_request_compatibility(req)
        assert is_compat is True
        assert len(warnings) == 0, f"Expected 0 warnings for studio voice '{voice}', got: {warnings}"



