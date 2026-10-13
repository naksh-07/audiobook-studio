import os
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from audiobook_factory.character_caster import (
    CharacterCaster,
    HONORIFIC_BLACKLIST,
    MALE_VOICE_PERSONAS,
    FEMALE_CHARACTER_VOICE_PERSONAS,
)
from audiobook_factory.casting.phonetic_transliteration import (
    derive_devanagari_name,
    is_devanagari,
)
from audiobook_factory.casting.cast_lock import CastLockManager
from audiobook_factory.casting.director import StudioCastingDirector
from audiobook_factory.preproduction.lexical_scanner import is_stopword, ENGLISH_NON_ENTITY_STOPWORDS
from audiobook_factory.preproduction.preproduction_supervisor import PreProductionSupervisor
from audiobook_factory.preproduction.novel_deepsearch import DeepSearchNovelDossier
from audiobook_factory.preproduction.vocal_acoustic_director import VocalSpacesManifest
from audiobook_factory.metadata.book_bible import BookBible


def test_defect1_character_consolidation_honorific_blacklist():
    assert 'sir' in HONORIFIC_BLACKLIST
    assert 'lord' in HONORIFIC_BLACKLIST
    assert 'master' in HONORIFIC_BLACKLIST
    assert 'alderman' in HONORIFIC_BLACKLIST
    assert 'लोर्ड' in HONORIFIC_BLACKLIST
    assert 'किन्ग' in HONORIFIC_BLACKLIST

    raw_characters = [
        {'canonical_name': 'Geralt of Rivia', 'aliases': ['Witcher', 'White Wolf'], 'gender': 'male'},
        {'canonical_name': 'Witcher', 'aliases': [], 'gender': 'male'},
        {'canonical_name': 'Sir Borch of Three Jackdaws', 'aliases': ['Borch', 'Three Jackdaws'], 'gender': 'male'},
        {'canonical_name': 'Sir Eyck of Denesle', 'aliases': ['Eyck'], 'gender': 'male'},
        {'canonical_name': 'Alderman of Blaviken', 'aliases': ['Alderman'], 'gender': 'male'},
        {'canonical_name': 'Master Chappelle', 'aliases': ['Chappelle'], 'gender': 'male'},
        {'canonical_name': 'Yennefer of Vengerberg', 'aliases': [], 'gender': 'female'},
        {'canonical_name': 'Yen', 'aliases': [], 'gender': 'female'},
        {'canonical_name': 'Essi', 'aliases': ['Little Eye'], 'gender': 'female'},
        {'canonical_name': 'Little Eye', 'aliases': [], 'gender': 'male'},
        {'canonical_name': 'Dainty', 'aliases': ['Biberveldt'], 'gender': 'male'},
        {'canonical_name': 'Biberveldt', 'aliases': [], 'gender': 'male'},
    ]

    consolidated = CharacterCaster.consolidate_characters(raw_characters)
    assert len(consolidated) == 8

    names = {c.get('canonical_name') for c in consolidated}
    assert 'Geralt of Rivia' in names
    assert 'Witcher' not in names, "Witcher should merge into Geralt of Rivia"
    assert 'Sir Borch of Three Jackdaws' in names
    assert 'Sir Eyck of Denesle' in names
    assert 'Alderman of Blaviken' in names
    assert 'Master Chappelle' in names
    assert 'Yennefer of Vengerberg' in names
    assert 'Essi' in names
    assert 'Little Eye' not in names, "Little Eye should merge into Essi"
    assert 'Dainty Biberveldt' in names, "Dainty and Biberveldt should merge into Dainty Biberveldt"

    yen = next(c for c in consolidated if c.get('canonical_name') == 'Yennefer of Vengerberg')
    assert 'Yen' in yen.get('aliases', [])

    geralt = next(c for c in consolidated if c.get('canonical_name') == 'Geralt of Rivia')
    assert 'Witcher' in geralt.get('aliases', [])

    essi = next(c for c in consolidated if c.get('canonical_name') == 'Essi')
    assert 'Little Eye' in essi.get('aliases', [])
    assert essi.get('gender') == 'female'


def test_defect2_stopword_seed_rejection_and_force_flag(tmp_path):
    ext_dir = tmp_path / 'extracted'
    ext_dir.mkdir(parents=True, exist_ok=True)
    (ext_dir / 'chapter_001.md').write_text('Geralt traveled near Brokilon. The Alderman spoke.', encoding='utf-8')
    (tmp_path / 'metadata.json').write_text(json.dumps({'title': 'Defect2 Novel', 'project_slug': 'defect2_novel'}), encoding='utf-8')

    tainted_roster = {
        'project_id': 'proj-defect2',
        'characters': {
            'Did': {'english_name': 'Did', 'gender': 'male'},
            'Have': {'english_name': 'Have', 'gender': 'male'},
            'Hey': {'english_name': 'Hey', 'gender': 'male'},
            'Don': {'english_name': 'Don', 'gender': 'male'},
            'Gods': {'english_name': 'Gods', 'gender': 'male'},
            'Geralt': {'english_name': 'Geralt', 'gender': 'male'},
        }
    }
    (tmp_path / 'character_roster.json').write_text(json.dumps(tainted_roster), encoding='utf-8')

    supervisor = PreProductionSupervisor(model='mock-model')

    mock_dossier = DeepSearchNovelDossier(
        book_title='Defect2 Novel',
        author='Author',
        project_slug='defect2_novel',
        world_lore_entities={
            'locations': {'Brokilon': 'ब्रोकिलोन'},
        }
    )
    mock_chars = [
        {'english_name': 'Geralt', 'hindi_name': 'गेराल्ट', 'gender': 'male'},
        {'english_name': 'Brokilon', 'hindi_name': 'ब्रोकिलोन', 'gender': 'neutral'},
        {'english_name': 'Did', 'hindi_name': 'डिड', 'gender': 'male'},
    ]
    mock_vocal = VocalSpacesManifest(project_id='proj-defect2', book_title='Defect2 Novel')
    mock_sonic = {'acoustic_spaces': {}, 'signature_foley_palettes': {}}
    mock_lex = {'locations': {'Brokilon': 'ब्रोकिलोन'}}
    mock_dna = {'literary_tradition': 'FANTASY', 'source_fidelity_tier': 'RAW_UNRATED'}

    with patch.object(supervisor.deepsearch, 'conduct_deepsearch', return_value=mock_dossier), \
         patch.object(supervisor.book_dna_agent, 'analyze_book_dna', return_value=mock_dna), \
         patch.object(supervisor.dramatis_personae_agent, 'extract_dramatis_personae', return_value=mock_chars), \
         patch.object(supervisor.vocal_director, 'design_vocal_spaces', return_value=mock_vocal), \
         patch.object(supervisor.sonic_architect, 'design_sonic_bible', return_value=mock_sonic), \
         patch.object(supervisor.lexicon_dramaturge, 'extract_lexicon_and_phonetics', return_value=mock_lex):

        res = supervisor.execute_preproduction(project_dir=tmp_path, force=True)
        assert res['status'] == 'MASTER_LOCKED'

    bible_path = tmp_path / 'book_bible.json'
    assert bible_path.exists()
    bible_data = json.loads(bible_path.read_text(encoding='utf-8'))

    for stopw in ('Did', 'Have', 'Hey', 'Don', 'Gods'):
        assert stopw not in bible_data.get('characters', {}), f'Stopword {stopw} leaked into book_bible.characters!'

    assert 'Brokilon' not in bible_data.get('characters', {}), 'Location Brokilon should not be in characters!'
    assert 'Brokilon' in bible_data.get('locations', {}), 'Location Brokilon must be in book_bible.locations!'


def test_defect3_voice_allocation_and_archetype_anchors():
    expected_males = {'Fenrir', 'Orus', 'Algieba', 'Achird', 'Algenib', 'Enceladus', 'Puck', 'Zephyr', 'Charon'}
    assert set(MALE_VOICE_PERSONAS) == expected_males
    assert len(MALE_VOICE_PERSONAS) == 9

    expected_females = {'Kore', 'Leda', 'Achernar', 'Callisto'}
    assert set(FEMALE_CHARACTER_VOICE_PERSONAS) == expected_females
    assert len(FEMALE_CHARACTER_VOICE_PERSONAS) == 4

    raw_characters = [
        {'canonical_name': 'Dandelion', 'gender': 'male', 'archetype': 'witty bard companion minstrel'},
        {'canonical_name': 'Yennefer', 'gender': 'female', 'archetype': 'commanding regal sorceress'},
        {'canonical_name': 'Ciri', 'gender': 'female', 'archetype': 'young maiden daughter'},
        {'canonical_name': 'Alderman', 'gender': 'male', 'archetype': 'disciplined town official'},
        {'canonical_name': 'Geralt', 'gender': 'male', 'archetype': 'stoic mutant hunter'},
        {'canonical_name': 'Innkeeper', 'gender': 'male', 'archetype': 'warm tavern keeper commoner'},
    ]

    roster, registry, cast_lock = CharacterCaster._build_cast_allocation(
        project_id='proj-defect3',
        raw_characters=raw_characters,
        use_hindi=True,
    )

    assert registry['Narrator']['voice'] == 'Aoede'
    assert registry['Narrator']['pitch'] == 1.0
    assert registry['Narrator']['speed'] == 1.0

    assert registry['Dandelion']['voice'] == 'Puck'
    assert registry['Dandelion']['pitch'] == 1.0
    assert registry['Dandelion']['speed'] == 1.0

    assert registry['Yennefer']['voice'] == 'Kore'

    assert registry['Ciri']['voice'] in ('Leda', 'Achernar')
    assert registry['Ciri']['pitch'] == 1.0

    for name, cfg in registry.items():
        p = cfg['pitch']
        assert 0.88 <= p <= 1.12, f'Pitch {p} for {name} violated hard bounds [0.88, 1.12]!'
        assert 0.94 <= p <= 1.06, f'Pitch {p} for {name} violated safe bounds [0.94, 1.06]!'


    for forbidden in ('Lord', 'Sir', 'Master', 'लोर्ड', 'किन्ग', 'lord', 'sir'):
        assert forbidden not in cast_lock.get('locks', {}), f"Standalone generic key '{forbidden}' leaked into cast_lock.json!"


def test_defect4_bilingual_devanagari_resolution_in_cast_lock(tmp_path):
    director = StudioCastingDirector(project_dir=tmp_path)

    characters = [
        {'canonical_name': 'Town Alderman', 'aliases': ['Alderman']},
        {'canonical_name': 'Three Jackdaws', 'aliases': ['Borch']},
        {'canonical_name': 'Ciri', 'aliases': ['Cirilla']},
        {'canonical_name': 'Dandelion', 'aliases': ['Jaskier']},
        {'canonical_name': 'Geralt of Rivia', 'aliases': ['Witcher']},
        {'canonical_name': 'Yennefer of Vengerberg', 'aliases': ['Yen']},
    ]

    manifest = director.cast_ensemble_from_roster(characters, use_hindi=True)

    lock_alderman = manifest.get_lock('एल्डरमैन')
    assert lock_alderman is not None
    assert lock_alderman.character_name == 'Town Alderman'

    lock_three_jackdaws = manifest.get_lock('थ्री जैकडॉज़')
    assert lock_three_jackdaws is not None
    assert lock_three_jackdaws.character_name == 'Three Jackdaws'

    # Whole-word token matching for non-honorific token
    lock_borch = manifest.get_lock('बोर्च')
    assert lock_borch is not None
    assert lock_borch.character_name == 'Three Jackdaws'

    # Eyck both Devanagari spellings
    p_eyck, a_eyck = derive_devanagari_name('Eyck')
    assert 'आइक' in a_eyck
    assert 'आईक' in a_eyck

    lock_ciri = manifest.get_lock('सिरी')
    assert lock_ciri is not None
    assert lock_ciri.character_name == 'Ciri'

    lock_dandelion = manifest.get_lock('डैंडेलियन')
    assert lock_dandelion is not None
    assert lock_dandelion.character_name == 'Dandelion'

    lock_geralt = manifest.get_lock('गेराल्ट')
    assert lock_geralt is not None
    assert lock_geralt.character_name == 'Geralt of Rivia'

    lock_yen = manifest.get_lock('येनेफ़र')
    assert lock_yen is not None
    assert lock_yen.character_name == 'Yennefer of Vengerberg'

    reg_file = tmp_path / 'voice_registry.json'
    assert reg_file.exists()
    reg = json.loads(reg_file.read_text(encoding='utf-8'))

    expected_keys = [
        'Town Alderman', 'एल्डरमैन',
        'Three Jackdaws', 'थ्री जैकडॉज़',
        'Ciri', 'सिरी',
        'Dandelion', 'डैंडेलियन',
        'Geralt of Rivia', 'गेराल्ट',
        'Yennefer of Vengerberg', 'येनेफ़र',
    ]
    for ek in expected_keys:
        assert ek in reg, f'Expected key {ek} missing from voice_registry.json!'


def test_defect5_lexical_scanner_stopwords():
    stopwords_to_test = [
        'God', 'Gods', 'Goddess', 'Goddesses',
        'Lordship', 'Ladyship', 'Majesty', 'Grace', 'Highness',
        'Did', 'Have', 'Hey', 'Don',
        'Get', 'Got', 'Gets', 'Getting', 'Gotten',
    ]
    for sw in stopwords_to_test:
        assert is_stopword(sw), f'{sw} should be recognized as a stopword!'
        assert sw in ENGLISH_NON_ENTITY_STOPWORDS or sw.title() in ENGLISH_NON_ENTITY_STOPWORDS

    valid_names = ['Geralt', 'Yennefer', 'Ciri', 'Dandelion', 'Borch', 'Eyck', 'Chappelle', 'Alderman']
    for vn in valid_names:
        assert not is_stopword(vn), f'Character {vn} was incorrectly classified as a stopword!'


def test_remediation1_unify_essi_daven_and_dainty_biberveldt():
    raw_characters = [
        {'canonical_name': 'Essi Daven', 'aliases': [], 'gender': 'female'},
        {'canonical_name': 'Little Eye', 'aliases': [], 'gender': 'neutral'},
        {'canonical_name': 'Dainty', 'aliases': [], 'gender': 'male'},
        {'canonical_name': 'Biberveldt', 'aliases': [], 'gender': 'neutral'},
        {'canonical_name': 'Arthur', 'aliases': []},
        {'canonical_name': 'Dent', 'aliases': []},
    ]
    # In corpus, Arthur Dent appears
    corpus = "Arthur Dent looked at the stars."
    consolidated = CharacterCaster.consolidate_characters(raw_characters, corpus=corpus)

    names = {c.get('canonical_name') for c in consolidated}
    assert 'Essi Daven' in names
    assert 'Little Eye' not in names
    assert 'Dainty Biberveldt' in names
    assert 'Dainty' not in names
    assert 'Biberveldt' not in names
    assert 'Arthur Dent' in names

    essi = next(c for c in consolidated if c.get('canonical_name') == 'Essi Daven')
    assert essi.get('gender') == 'female'
    assert 'Little Eye' in essi.get('aliases', [])
    assert 'लिटिल आई' in essi.get('aliases', [])

    dainty = next(c for c in consolidated if c.get('canonical_name') == 'Dainty Biberveldt')
    assert dainty.get('gender') == 'male'
    assert 'Dainty' in dainty.get('aliases', [])
    assert 'Biberveldt' in dainty.get('aliases', [])


def test_remediation2_relocate_brokilon_forest_and_locations(tmp_path):
    ext_dir = tmp_path / 'extracted'
    ext_dir.mkdir(parents=True, exist_ok=True)
    (ext_dir / 'chapter_001.md').write_text('Geralt traveled near Brokilon Forest.', encoding='utf-8')
    (tmp_path / 'metadata.json').write_text(json.dumps({'title': 'Forest Novel', 'project_slug': 'forest_novel'}), encoding='utf-8')

    supervisor = PreProductionSupervisor(model='mock-model')

    mock_dossier = DeepSearchNovelDossier(
        book_title='Forest Novel',
        author='Author',
        project_slug='forest_novel',
        world_lore_entities={'locations': {}}  # Brokilon NOT in dossier locations
    )
    mock_chars = [
        {'english_name': 'Geralt', 'hindi_name': 'गेराल्ट', 'gender': 'male'},
        {'english_name': 'Brokilon', 'hindi_name': 'ब्रोकिलोन', 'gender': 'neutral'},
        {'english_name': 'Novigrad Port', 'hindi_name': 'नोविग्राड पोर्ट', 'gender': 'neutral'},
    ]
    mock_vocal = VocalSpacesManifest(project_id='proj-forest', book_title='Forest Novel')
    mock_sonic = {'acoustic_spaces': {}, 'signature_foley_palettes': {}}
    mock_lex = {'locations': {}}
    mock_dna = {'literary_tradition': 'FANTASY', 'source_fidelity_tier': 'RAW_UNRATED'}

    with patch.object(supervisor.deepsearch, 'conduct_deepsearch', return_value=mock_dossier), \
         patch.object(supervisor.book_dna_agent, 'analyze_book_dna', return_value=mock_dna), \
         patch.object(supervisor.dramatis_personae_agent, 'extract_dramatis_personae', return_value=mock_chars), \
         patch.object(supervisor.vocal_director, 'design_vocal_spaces', return_value=mock_vocal), \
         patch.object(supervisor.sonic_architect, 'design_sonic_bible', return_value=mock_sonic), \
         patch.object(supervisor.lexicon_dramaturge, 'extract_lexicon_and_phonetics', return_value=mock_lex):

        res = supervisor.execute_preproduction(project_dir=tmp_path, force=True)
        assert res['status'] == 'MASTER_LOCKED'

    bible_data = json.loads((tmp_path / 'book_bible.json').read_text(encoding='utf-8'))
    assert 'Brokilon' not in bible_data.get('characters', {})
    assert 'Brokilon' in bible_data.get('locations', {})
    assert 'Novigrad Port' not in bible_data.get('characters', {})
    assert 'Novigrad Port' in bible_data.get('locations', {})


def test_remediation3_alderman_gender_male():
    from audiobook_factory.preproduction.linguistic_gender_resolver import LinguisticGenderResolver

    corpus = "The wife of the Alderman greeted the guests at the reception. She was wearing silk."
    ev = LinguisticGenderResolver.resolve_gender("Alderman", corpus)
    assert ev.gender == "male"
    assert ev.male_score > ev.female_score

    ev_empty = LinguisticGenderResolver.resolve_gender("Alderman", "")
    assert ev_empty.gender == "male"


def test_remediation4_purge_standalone_prepositions_numbers_adjectives_honorifics(tmp_path):
    # 1. derive_devanagari_name compound splitting and epithets
    p_little_eye, a_little_eye = derive_devanagari_name("Little Eye", aliases=["Little", "Eye", "लिटिल", "आई"])
    assert p_little_eye == "लिटिल आई"
    assert "लिटिल आई" in a_little_eye
    for forbidden in ("Little", "Eye", "लिटिल", "आई", "एे", "three", "थ्री"):
        assert forbidden not in a_little_eye, f"Standalone token '{forbidden}' leaked into dev_aliases!"

    p_three, a_three = derive_devanagari_name("Three Jackdaws")
    assert "थ्री जैकडॉज़" in a_three
    assert "थ्री" not in a_three
    assert "three" not in a_three

    # 2. cast_lock and voice_registry
    director = StudioCastingDirector(project_dir=tmp_path)
    characters = [
        {
            'canonical_name': 'Essi Daven',
            'aliases': ['Little Eye', 'Little', 'Eye', 'लिटिल आई', 'लिटिल', 'आई'],
            'gender': 'female',
        },
        {
            'canonical_name': 'Three Jackdaws',
            'aliases': ['Borch', 'Three', 'three', 'थ्री', 'थ्री जैकडॉज़'],
            'gender': 'male',
        },
    ]

    manifest = director.cast_ensemble_from_roster(characters, use_hindi=True)
    reg_file = tmp_path / 'voice_registry.json'
    reg = json.loads(reg_file.read_text(encoding='utf-8'))

    # Allowed valid keys
    assert 'Essi Daven' in reg
    assert 'Little Eye' in reg
    assert 'लिटिल आई' in reg
    assert 'Three Jackdaws' in reg
    assert 'थ्री जैकडॉज़' in reg
    assert 'बोर्च' in reg

    # Purged forbidden standalone keys
    forbidden_keys = (
        'Little', 'Eye', 'लिटिल', 'आई', 'एे',
        'Three', 'three', 'थ्री',
        'of', 'the', 'lord', 'sir', 'master',
        'ओफ़', 'ऑफ़', 'सिर', 'मास्टेर',
    )
    for fk in forbidden_keys:
        assert fk not in reg, f"Forbidden standalone key '{fk}' leaked into voice_registry.json!"


def test_round5_defect1_and_defect2_eyck_alderman_brokilon(tmp_path):
    ext_dir = tmp_path / 'extracted'
    ext_dir.mkdir(parents=True, exist_ok=True)
    chapter_text = "Sir Eyck of Denesle rode his stallion toward Brokilon. 'Have you forgotten, Alderman?' cried the fat Alderman."
    (ext_dir / 'chapter_001.md').write_text(chapter_text, encoding='utf-8')
    (tmp_path / 'metadata.json').write_text(json.dumps({'title': 'Round5 Novel', 'project_slug': 'round5_novel'}), encoding='utf-8')

    supervisor = PreProductionSupervisor(model='mock-model')

    mock_dossier = DeepSearchNovelDossier(
        book_title='Round5 Novel',
        author='Author',
        project_slug='round5_novel',
        world_lore_entities={
            'locations': {'Denesle': 'डेनेस्ले', 'Brokilon': 'ब्रोकिलोन'},
            'terminology': {'Alderman': 'एल्डरमैन'},
        }
    )
    mock_chars = [
        {'english_name': 'Eyck of Denesle', 'hindi_name': 'आइक ऑफ़ डेनेस्ले', 'gender': 'male', 'sociolect_trait': 'chivalric holy knight'},
        {'english_name': 'Denesle', 'hindi_name': 'डेनेस्ले', 'gender': 'neutral'},
        {'english_name': 'Brokilon', 'hindi_name': 'ब्रोकिलोन', 'gender': 'neutral'},
    ]
    mock_vocal = VocalSpacesManifest(project_id='proj-round5', book_title='Round5 Novel')
    mock_sonic = {'acoustic_spaces': {}, 'signature_foley_palettes': {}}
    mock_lex = {'locations': {'Denesle': 'डेनेस्ले', 'Brokilon': 'ब्रोकिलोन'}}
    mock_dna = {'literary_tradition': 'FANTASY', 'source_fidelity_tier': 'RAW_UNRATED'}

    with patch.object(supervisor.deepsearch, 'conduct_deepsearch', return_value=mock_dossier), \
         patch.object(supervisor.book_dna_agent, 'analyze_book_dna', return_value=mock_dna), \
         patch.object(supervisor.dramatis_personae_agent, 'extract_dramatis_personae', return_value=mock_chars), \
         patch.object(supervisor.vocal_director, 'design_vocal_spaces', return_value=mock_vocal), \
         patch.object(supervisor.sonic_architect, 'design_sonic_bible', return_value=mock_sonic), \
         patch.object(supervisor.lexicon_dramaturge, 'extract_lexicon_and_phonetics', return_value=mock_lex):

        res = supervisor.execute_preproduction(project_dir=tmp_path, force=True)
        assert res['status'] == 'MASTER_LOCKED'

    bible_data = json.loads((tmp_path / 'book_bible.json').read_text(encoding='utf-8'))
    cast_lock_data = json.loads((tmp_path / 'cast_lock.json').read_text(encoding='utf-8'))

    # DEFECT 1: Eyck of Denesle must NOT be purged by substring match of 'denesle' in locations
    assert 'Eyck of Denesle' in bible_data['characters'], "Eyck of Denesle was purged by location substring bug!"
    assert 'Denesle' not in bible_data['characters'], "Denesle should be in locations, not characters!"
    assert 'Denesle' in bible_data['locations']

    # DEFECT 2: Alderman must be in bible.characters as male with authentic voice
    assert 'Alderman' in bible_data['characters'], "Alderman missing from book_bible.characters!"
    ald_entity = bible_data['characters']['Alderman']
    assert ald_entity['gender'] == 'male'
    assert ald_entity['hindi_name'] == 'एल्डरमैन'

    # Brokilon must be in bible.locations
    assert 'Brokilon' in bible_data['locations']
    assert bible_data['locations']['Brokilon'] == 'ब्रोकिलोन'

    # Alderman voice check in cast_lock
    ald_lock = cast_lock_data['locks'].get('Alderman')
    assert ald_lock is not None
    assert ald_lock['voice_id'] in ('Orus', 'Fenrir', 'Achird')


def test_round5_defect3_mojibake_diacritics_transliteration():
    from audiobook_factory.casting.phonetic_transliteration import (
        transliterate_to_devanagari,
        rule_based_latin_to_devanagari,
        derive_devanagari_name,
    )

    # 1. Vocabulary entries
    assert transliterate_to_devanagari("véa") == "वेया"
    assert transliterate_to_devanagari("Véa") == "वेया"
    assert transliterate_to_devanagari("téa") == "तेया"
    assert transliterate_to_devanagari("Téa") == "तेया"
    assert transliterate_to_devanagari("vea") == "वेया"
    assert transliterate_to_devanagari("tea") == "तेया"
    assert transliterate_to_devanagari("eyck") == "आइक"
    assert transliterate_to_devanagari("eyck of denesle") == "आइक ऑफ़ डेनेस्ले"

    # 2. Rule-based fallback: accented vowels should normalize and not cause Mojibake
    res_accented = rule_based_latin_to_devanagari("Hélène")
    assert "é" not in res_accented
    assert "e" not in res_accented
    assert is_devanagari(res_accented)

    res_accented2 = rule_based_latin_to_devanagari("Clémence")
    assert "é" not in res_accented2
    assert is_devanagari(res_accented2)

    # 3. Eyck must contain BOTH 'आइक' and 'आईक' in dev_aliases
    p_eyck, a_eyck = derive_devanagari_name("Eyck")
    assert "आइक" in a_eyck
    assert "आईक" in a_eyck


def test_round5_defect4_forbidden_keys_and_prepositional_phrases(tmp_path):
    from audiobook_factory.character_caster import _is_blacklisted_or_generic
    from audiobook_factory.casting.cast_lock import _is_standalone_forbidden_key

    # Generic titles & roles
    generic_roles = ("chancellor", "चान्सेल्लोर", "leader", "लीडेर", "mistress", "मिस्ट्रेस्स")
    for gr in generic_roles:
        assert _is_blacklisted_or_generic(gr), f"{gr} should be blacklisted in _is_blacklisted_or_generic"
        assert _is_standalone_forbidden_key(gr), f"{gr} should be forbidden in _is_standalone_forbidden_key"

    # Prepositional phrases
    prep_phrases = ("of the", "ओफ़ थे", "ऑफ़ द", "लीडेर ओफ़", "लीडेर ओफ़ थे", "leader of", "leader of the")
    for pp in prep_phrases:
        assert _is_blacklisted_or_generic(pp), f"{pp} should be blacklisted in _is_blacklisted_or_generic"
        assert _is_standalone_forbidden_key(pp), f"{pp} should be forbidden in _is_standalone_forbidden_key"

    # Reject aliases starting or ending with connector
    connector_edges = ("of Blaviken", "the Alderman", "डेनेस्ले का", "लीडेर ओफ़", "लॉर्ड से", "की रानी")
    for ce in connector_edges:
        assert _is_blacklisted_or_generic(ce), f"Edge-connector '{ce}' should be blacklisted!"
        assert _is_standalone_forbidden_key(ce), f"Edge-connector '{ce}' should be forbidden!"

    # Person with origin of location is valid
    assert not _is_blacklisted_or_generic("Eyck of Denesle")
    assert not _is_standalone_forbidden_key("Eyck of Denesle")
    assert not _is_blacklisted_or_generic("Alderman of Blaviken")

    # Verify cast_lock and voice_registry never register forbidden keys
    director = StudioCastingDirector(project_dir=tmp_path)
    characters = [
        {
            'canonical_name': 'Eyck of Denesle',
            'aliases': [
                'Eyck', 'Sir Eyck', 'Chancellor', 'चान्सेल्लोर', 'Leader', 'लीडेर',
                'Mistress', 'मिस्ट्रेस्स', 'of the', 'ओफ़ थे', 'ऑफ़ द', 'लीडेर ओफ़',
                'लीडेर ओफ़ थे', 'of Denesle', 'डेनेस्ले का', 'Holy Knight',
            ],
            'gender': 'male',
        }
    ]

    manifest = director.cast_ensemble_from_roster(characters, use_hindi=True)
    reg_file = tmp_path / 'voice_registry.json'
    reg = json.loads(reg_file.read_text(encoding='utf-8'))

    # Valid keys present
    assert 'Eyck of Denesle' in reg
    assert 'Holy Knight' in reg
    assert 'आइक' in reg

    # Forbidden keys absent
    forbidden = (
        'Chancellor', 'चान्सेल्लोर', 'Leader', 'लीडेर', 'Mistress', 'मिस्ट्रेस्स',
        'of the', 'ओफ़ थे', 'ऑफ़ द', 'लीडेर ओफ़', 'लीडेर ओफ़ थे',
        'of Denesle', 'डेनेस्ले का', 'of', 'the', 'ओफ़', 'थे', 'का', 'की', 'के', 'से'
    )
    for fk in forbidden:
        assert fk not in reg, f"Forbidden key '{fk}' leaked into voice_registry.json!"
        assert fk not in manifest.locks, f"Forbidden key '{fk}' leaked into manifest.locks!"


def test_round6_defect1_descriptive_phrases_and_generic_blacklist(tmp_path):
    """Verify Round 6 fixes: descriptive phrase anti-splitting and generic token blacklist."""
    from audiobook_factory.casting.phonetic_transliteration import derive_devanagari_name
    from audiobook_factory.character_caster import _is_blacklisted_or_generic, CharacterCaster
    from audiobook_factory.casting.cast_lock import _is_standalone_forbidden_key, CastLockManager

    # 1. derive_devanagari_name must NOT split 3+ word descriptive phrases into single tokens
    _, dev_aliases = derive_devanagari_name(
        "Alderman",
        aliases=["fat man in yellow jerkin", "Town Alderman"]
    )
    assert "मान" not in dev_aliases, "Generic noun 'मान' extracted from descriptive phrase!"
    assert "फ़ाट" not in dev_aliases
    assert "येल्लोव" not in dev_aliases
    assert "जेर्किन" not in dev_aliases
    assert "मान इन" not in dev_aliases
    assert "फ़ाट मान" not in dev_aliases

    # 2. Generic occupations, titles, numbers, and descriptors
    generic_keys = (
        "man", "मान", "fat", "फ़ाट", "yellow", "येल्लोव", "jerkin", "जेर्किन",
        "cobbler", "कोब्ब्लेर", "sorcerer", "सोर्सेरेर", "sorceress", "सोर्सेरेस्स",
        "halberdier", "हाल्बेर्डिेर", "warrior", "वार्रिोर", "reaver", "रीवेर",
        "denesle", "डेनेस्ले", "golden", "गोल्डेन", "dragon", "ड्रागोन", "little", "लिट्ट्ले"
    )
    for gk in generic_keys:
        assert _is_blacklisted_or_generic(gk), f"'{gk}' must be blacklisted in _is_blacklisted_or_generic"
        assert _is_standalone_forbidden_key(gk), f"'{gk}' must be forbidden in _is_standalone_forbidden_key"

    # 3. Ensure _build_cast_allocation never registers any of these as standalone keys in locks
    characters = [
        {
            "canonical_name": "Alderman",
            "aliases": ["Town Alderman", "fat man in yellow jerkin", "man", "मान"],
            "gender": "male",
            "archetype": "disciplined town official",
        },
        {
            "canonical_name": "Sheepbagger",
            "aliases": ["Cobbler", "कोब्ब्लेर", "Master Cobbler"],
            "gender": "male",
            "archetype": "poor peasant cobbler",
        }
    ]
    roster, vreg, cast_lock = CharacterCaster._build_cast_allocation(
        project_id="proj-round6-test",
        raw_characters=characters,
        use_hindi=True,
    )
    locks = cast_lock["locks"]
    for gk in ("man", "मान", "fat", "फ़ाट", "yellow", "येल्लोव", "jerkin", "जेर्किन", "Cobbler", "कोब्ब्लेर"):
        assert gk not in locks, f"Generic key '{gk}' must not be a standalone key in locks!"


def test_round6_defect2_tea_reinstatement_and_sword_of_destiny_assets():
    """Verify Sword of Destiny project assets: Téa reinstatement and zero generic key collisions."""
    from audiobook_factory.casting.cast_lock import CastLockManager

    p = Path("audiobooks/projects/sword_of_destiny_-_andrzej_sapkowski")
    if not p.exists():
        pytest.skip("Sword of Destiny project not found")

    cl_mgr = CastLockManager(p)

    # 1. get_lock('मान') must be None (0 collision)
    lock_maan = cl_mgr.get_lock("मान")
    assert lock_maan is None, f"Expected None for 'मान', got {lock_maan}"

    # 2. get_lock('Téa') and get_lock('तेया') must resolve to Téa (female, Achernar)
    lock_tea_en = cl_mgr.get_lock("Téa")
    assert lock_tea_en is not None, "Expected lock for 'Téa'"
    assert lock_tea_en.voice_id == "Achernar", f"Expected voice 'Achernar', got {lock_tea_en.voice_id}"

    lock_tea_hi = cl_mgr.get_lock("तेया")
    assert lock_tea_hi is not None, "Expected lock for 'तेया'"
    assert lock_tea_hi.voice_id == "Achernar", f"Expected voice 'Achernar', got {lock_tea_hi.voice_id}"

    lock_tea_ascii = cl_mgr.get_lock("Tea")
    assert lock_tea_ascii is not None
    assert lock_tea_ascii.voice_id == "Achernar"

    # 3. Verify clean disk assets
    cl = json.loads((p / "cast_lock.json").read_text(encoding="utf-8"))
    vr = json.loads((p / "voice_registry.json").read_text(encoding="utf-8"))
    bb = json.loads((p / "book_bible.json").read_text(encoding="utf-8"))
    cr = json.loads((p / "character_roster.json").read_text(encoding="utf-8"))

    bad_keys = [
        "मान", "फ़ाट", "येल्लोव", "जेर्किन", "इन येल्लोव", "मान इन", "फ़ाट मान", "फ़ाट मान इन", "मान इन येल्लोव",
        "Cobbler", "कोब्ब्लेर", "Sorcerer", "सोर्सेरेर", "Sorceress", "सोर्सेरेस्स", "Halberdier", "हाल्बेर्डिेर",
        "डुके", "बारोन", "क्वीन", "मिस्स", "म्र्स", "वार्रिोर", "रीवेर", "डेनेस्ले", "गोल्डेन", "ड्रागोन", "लिट्ट्ले"
    ]
    for bk in bad_keys:
        assert bk not in cl.get("locks", {}), f"Bad key '{bk}' found in cast_lock.json!"
        assert bk not in vr, f"Bad key '{bk}' found in voice_registry.json!"

    # 4. Téa in all 4 files
    assert "Téa" in bb["characters"]
    assert bb["characters"]["Téa"]["assigned_voice"] == "Achernar"
    assert bb["characters"]["Téa"]["gender"] == "female"
    assert "Téa" in cr["characters"]
    assert cr["characters"]["Téa"]["assigned_voice_id"] == "Achernar"
    assert cr["characters"]["Téa"]["gender"] == "female"
    assert "Téa" in cl["locks"] and "तेया" in cl["locks"]
    assert "Téa" in vr and "तेया" in vr
    assert vr["Téa"]["voice"] == "Achernar"
    assert vr["तेया"]["voice"] == "Achernar"


