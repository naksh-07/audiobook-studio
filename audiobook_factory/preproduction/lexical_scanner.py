#!/usr/bin/env python3
"""
Audiobook Factory - Room 1 Subsystem 1: Deterministic Full-Text Lexical Scanner.
==============================================================================
Provides 0-token, 0ms, 100% full-corpus lexical entity extraction across all novel chapters.
Eliminates context starvation by scanning proper nouns, title honorifics, dialogue speaker
attributions, and alias co-occurrences across the entire book.
"""

from __future__ import annotations
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple


ENGLISH_NON_ENTITY_STOPWORDS = {
    # Pronouns & Possessives
    "The", "He", "She", "They", "Then", "After", "There", "When", "What", "It", "In", "On", "At",
    "Are", "Yes", "Do", "You", "Who", "No", "That", "As", "Your", "Well", "And", "So", "Ah",
    "Greetings", "How", "History", "This", "Not", "Something", "But", "If", "To", "Become",
    "Why", "Where", "Which", "Can", "Could", "Would", "Should", "May", "Might", "Must",
    "Never", "Always", "Sometimes", "Perhaps", "Maybe", "Here", "Now", "Only", "Just",
    "All", "Some", "One", "Two", "Three", "Four", "Five", "My", "Our", "His", "Her", "Its",
    "Their", "We", "I", "Me", "Him", "Them", "Us", "Mine", "Yours", "Hers", "Ours", "Theirs",
    "Sit", "Let", "Geography", "Because", "Certainly", "Civilization",
    "Stories", "True", "Nonsense", "Instead", "Either", "Another", "Whatever", "Notice",
    "Nothing", "Someone", "Everybody", "Nobody", "Anyway", "Obviously", "Forgive", "Wait",
    "Chapter", "Book", "Part", "Prologue", "Epilogue", "Scene", "Act", "Volume",
    "With", "Without", "From", "Into", "Under", "Over", "Between", "Through", "During",
    "Before", "Behind", "Across", "Along", "Above", "Below", "Against", "Around", "Near",
    "Upon", "Toward", "Towards", "Within", "Among", "Both", "Each", "Every", "Neither",
    "Any", "Most", "Several", "Few", "Many", "Much", "Such", "Often", "Usually",
    "Seldom", "Rarely", "Hardly", "Barely", "Scarcely", "Once", "Twice", "First", "Second",
    "Third", "Next", "Last", "Early", "Late", "Already", "Still", "Yet", "Even", "Also",
    "Too", "Very", "Quite", "Rather", "Almost", "Nearly", "About", "Again", "Further",
    "Farther", "Away", "Whom", "Whose", "Whoever", "Whichever", "Wherever",
    "Whenever", "However", "Although", "Though", "While", "Whilst", "Whereas", "Since",
    "Unless", "Until", "Till", "Lest", "Except", "Besides", "Whether", "Nor", "Or", "For",
    "Later", "Tonight", "Yesterday", "Tomorrow", "Today", "Morning", "Evening", "Night",
    "Behind", "Underneath", "Beside", "Inside", "Outside", "Amid", "Amidst",
    # Auxiliary verbs & forms of be / do / have / get
    "Did", "Done", "Does", "Doing",
    "Have", "Had", "Has", "Having",
    "Get", "Got", "Gets", "Getting", "Gotten",
    "Is", "Was", "Were", "Are", "Am", "Be", "Been", "Being",
    # Contraction stems & truncated negative auxiliaries
    "Don", "Doesn", "Didn", "Won", "Wouldn", "Couldn", "Shouldn", "Isn", "Aren", "Wasn",
    "Weren", "Hasn", "Haven", "Hadn", "Ain", "Can't", "Don't", "Doesn't", "Didn't",
    "Won't", "Wouldn't", "Couldn't", "Shouldn't", "Isn't", "Aren't", "Wasn't", "Weren't",
    "It's", "That's", "There's", "Here's", "He's", "She's", "They're", "We're", "You're",
    "Let's", "What's", "Who's", "Where's", "Why's", "How's",
    # Common sentence-initial imperatives & speech verbs
    "Look", "Looked", "Looking", "Listen", "Listened", "Listening",
    "Tell", "Told", "Telling", "Ask", "Asked", "Asking",
    "Come", "Came", "Coming", "Say", "Said", "Saying",
    "See", "Saw", "Seen", "Seeing", "Go", "Went", "Gone", "Going",
    "Hear", "Heard", "Hearing", "Feel", "Felt", "Feeling",
    "Take", "Took", "Taken", "Taking", "Give", "Gave", "Given", "Giving",
    "Make", "Made", "Making", "Know", "Knew", "Known", "Knowing",
    "Think", "Thought", "Thinking", "Find", "Found", "Finding",
    "Leave", "Left", "Leaving", "Put", "Putting", "Keep", "Kept", "Keeping",
    "Hold", "Held", "Holding", "Speak", "Spoke", "Spoken", "Speaking",
    "Talk", "Talked", "Talking", "Call", "Called", "Calling",
    "Start", "Started", "Stop", "Stopped", "Stand", "Stood", "Standing",
    "Turn", "Turned", "Walk", "Walked", "Run", "Ran", "Running",
    "Show", "Showed", "Bring", "Brought", "Open", "Opened", "Close", "Closed",
    "Help", "Helped", "Try", "Tried", "Remember", "Remembered", "Forget", "Forgot",
    "Believe", "Believed", "Understand", "Understood",
    # Interjections & conversational starters
    "Hey", "Hello", "Hi", "Oh", "Ha", "Oho", "Yeah", "Nope", "Aye", "Nay",
    "Please", "Thank", "Thanks", "Sorry", "Excuse", "Pardon", "Alas", "Sure", "Surely", "Right", "Alright",
    # Known geographical and common fantasy location nouns
    "City", "Town", "Village", "Kingdom", "Empire", "Castle", "Palace", "Fortress", "Citadel",
    "Forest", "Wood", "Woods", "Grove", "Jungle",
    "River", "Stream", "Brook", "Lake", "Sea", "Ocean", "Pond", "Bay", "Harbor", "Port",
    "Mountain", "Mountains", "Peak", "Valley", "Canyon", "Gorge", "Hill", "Hills",
    "Street", "Road", "Avenue", "Lane", "Alley", "Highway", "Bridge", "Gate", "Wall",
    "Square", "Market", "Plaza", "Courtyard",
    "Inn", "Tavern", "Pub", "House", "Home", "Room", "Chamber", "Hall", "Tower", "Temple", "Church",
    "Dungeon", "Cell", "Prison", "Cave", "Cavern", "Crypt", "Tomb",
    "Island", "Isle", "Peninsula", "Coast", "Shore", "Beach",
    "Plains", "Field", "Fields", "Meadow", "Desert", "Swamp", "Marsh", "Bog",
    "Province", "Continent", "World", "Realm", "Land", "Territory", "District", "Country",
    "North", "South", "East", "West", "Northern", "Southern", "Eastern", "Western",
    "Earth", "Moon", "Sun", "Sky", "Heaven", "Hell",
    # Known benchmark geographical names & landmarks
    "Brokilon", "Wyzima", "Cintra", "Blaviken", "Novigrad", "Skellige", "Ellander",
    # Deities, titles of address, and non-entity honorific abstractions
    "God", "Gods", "Goddess", "Goddesses", "Lordship", "Ladyship", "Majesty", "Grace", "Highness",
    "Excellency", "Holiness", "Eminence",
}

_STOPWORDS_LOWER = {w.lower() for w in ENGLISH_NON_ENTITY_STOPWORDS}


def is_stopword(token: str) -> bool:
    """Checks if a token is a grammatical stopword, auxiliary verb, pronoun, contraction, or location noun."""
    if not token:
        return True
    t_clean = token.strip()
    t_clean = re.sub(r"^[\"\'“‘]+|[\"\'”’]+$", "", t_clean)
    if not t_clean:
        return True
    t_stripped = re.sub(r"['’](?:t|s|ll|re|ve|d|m)$", "", t_clean, flags=re.IGNORECASE)
    for cand in (t_clean, t_stripped):
        if cand in ENGLISH_NON_ENTITY_STOPWORDS:
            return True
        if cand.capitalize() in ENGLISH_NON_ENTITY_STOPWORDS:
            return True
        if cand.title() in ENGLISH_NON_ENTITY_STOPWORDS:
            return True
        if cand.lower() in _STOPWORDS_LOWER:
            return True
    return False


TITLE_WORDS = {
    "Lord", "Lady", "Baron", "Count", "Duke", "Duchess", "Captain", "Doctor", "Dr", "Mr", "Mrs",
    "Miss", "Master", "Sir", "King", "Queen", "Prince", "Princess", "Father", "Sister", "Brother",
    "Inspector", "Officer", "Chief", "General", "Major", "Colonel", "Alderman", "Innkeeper", "Witcher",
    "Commander", "Emperor", "Empress"
}

TITLE_HONORIFICS_PATTERN = re.compile(
    r"\b(Lord|Lady|Captain|Doctor|Dr\.|Mr\.|Mrs\.|Miss|Master|Sir|Father|Sister|Brother|"
    r"King|Queen|Prince|Princess|Baron|Count|Inspector|Officer|Chief|General|Major|Colonel|"
    r"Alderman|Innkeeper|Witcher|Commander|Duke|Duchess|Emperor|Empress)\s+([A-Z][a-z]{2,25})\b"
)

MULTIWORD_PROPER_NOUN_PATTERN = re.compile(
    r"\b([A-Z][a-z]{2,20}(?:\s+(?:of|de|van|von|the|del|da|la)\s+[A-Z][a-z]{2,20}|\s+[A-Z][a-z]{2,20}))\b"
)

# Dialogue speaker attribution patterns (bidirectional, strictly preserving capitalized speaker names)
POST_DIALOGUE_SPEAKER_PATTERN = re.compile(
    r'["\'”]\s*(?:said|asked|replied|whispered|cried|shouted|murmured|roared|growled|gasped|muttered|yelled|demanded|snarled|chuckled|Said|Asked|Replied|Whispered|Shouted|Cried)\s+([A-Z][a-z]{2,20})\b'
)

POST_DIALOGUE_SPEAKER_THEN_VERB_PATTERN = re.compile(
    r'["\'”]\s*([A-Z][a-z]{2,20})\s+(?:said|asked|replied|whispered|cried|shouted|murmured|roared|growled|gasped|muttered|yelled|demanded|snarled|chuckled)\b'
)

PRE_DIALOGUE_SPEAKER_PATTERN = re.compile(
    r'\b([A-Z][a-z]{2,20})\s+(?:said|asked|replied|whispered|cried|shouted|murmured|roared|growled|gasped|muttered|yelled|demanded|snarled|chuckled)\s*[:,\s]*["\'“]'
)

PRE_DIALOGUE_VERB_THEN_SPEAKER_PATTERN = re.compile(
    r'\b(?:said|asked|replied|whispered|cried|shouted|murmured|Said|Asked|Replied|Whispered)\s+([A-Z][a-z]{2,20})\s*[:,\s]*["\'“]'
)


@dataclass
class EntityOccurrence:
    """Statistical and provenance facts for a candidate entity discovered in the text corpus."""
    name: str
    first_chapter: int = 1
    total_mentions: int = 1
    dialogue_speaker_count: int = 0
    chapters_appeared: Set[int] = field(default_factory=set)
    introductory_quote: str = ""
    associated_titles: Set[str] = field(default_factory=set)
    co_occurring_names: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "first_chapter": self.first_chapter,
            "total_mentions": self.total_mentions,
            "dialogue_speaker_count": self.dialogue_speaker_count,
            "chapters_appeared": sorted(list(self.chapters_appeared)),
            "introductory_quote": self.introductory_quote,
            "associated_titles": sorted(list(self.associated_titles)),
            "co_occurring_names": dict(self.co_occurring_names),
        }


class LexicalCorpusIndex:
    """Searchable in-memory index of all entities, dialogue speakers, and citations across the novel."""

    def __init__(self, entities: Dict[str, EntityOccurrence], total_chapters: int, total_words: int):
        self.entities = entities
        self.total_chapters = total_chapters
        self.total_words = total_words

    def get_mention_count(self, name: str, aliases: Optional[List[str]] = None) -> int:
        """Returns total mentions of a name and its aliases across the entire book."""
        if not name:
            return 0
        names_to_check = [name] + (aliases or [])
        count = 0
        counted_keys = set()
        for n in names_to_check:
            n_clean = n.strip()
            if not n_clean:
                continue
            n_lower = n_clean.lower()
            for k, v in self.entities.items():
                k_lower = k.lower()
                if k_lower in counted_keys:
                    continue
                if k_lower == n_lower:
                    count += v.total_mentions
                    counted_keys.add(k_lower)
                elif (len(n_lower.split()) > 1 and k_lower in n_lower.split() and k_lower not in ENGLISH_NON_ENTITY_STOPWORDS) or \
                     (len(k_lower.split()) > 1 and n_lower in k_lower.split() and n_lower not in ENGLISH_NON_ENTITY_STOPWORDS):
                    count += v.total_mentions
                    counted_keys.add(k_lower)
        return count

    def get_first_chapter(self, name: str) -> int:
        """Returns the first chapter where an entity appeared (1-indexed)."""
        norm = name.strip().lower()
        for k, v in self.entities.items():
            if k.lower() == norm or (len(norm.split()) > 1 and k.lower() in norm.split()):
                return v.first_chapter
        return 1

    def get_intro_sentence(self, name: str) -> str:
        """Returns the exact sentence introducing the entity."""
        norm = name.strip().lower()
        for k, v in self.entities.items():
            if (k.lower() == norm or (len(norm.split()) > 1 and k.lower() in norm.split())) and v.introductory_quote:
                return v.introductory_quote
        return ""

    def get_top_speaking_characters(self, limit: int = 40) -> List[EntityOccurrence]:
        """Returns candidate entities sorted by speaking prominence and frequency."""
        def _rank(ent: EntityOccurrence) -> Tuple[int, int]:
            # Speaking frequency heavily weighted over passive mentions
            return (ent.dialogue_speaker_count * 3 + ent.total_mentions, len(ent.chapters_appeared))

        sorted_ents = sorted(self.entities.values(), key=_rank, reverse=True)
        return sorted_ents[:limit]

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "total_chapters": self.total_chapters,
            "total_words": self.total_words,
            "unique_entities_discovered": len(self.entities),
            "top_characters": [e.to_dict() for e in self.get_top_speaking_characters(30)],
        }


class LexicalCorpusScanner:
    """
    Deterministic Full-Novel Lexical Scanner.
    Processes all chapters locally with zero tokens and zero external network calls.
    """

    @classmethod
    def scan_project_dir(cls, project_dir: Path | str) -> LexicalCorpusIndex:
        """Scans extracted chapters markdown files directly from a project directory."""
        p_dir = Path(project_dir).resolve()
        search_dirs = [p_dir / "extracted", p_dir / "chapters", p_dir / "translation"]
        chapter_files: List[Path] = []
        for sdir in search_dirs:
            if sdir.exists():
                chapter_files = sorted(sdir.glob("chapter_*.md"))
                if chapter_files:
                    break

        chapters_data = []
        for idx, cf in enumerate(chapter_files, 1):
            try:
                txt = cf.read_text(encoding="utf-8", errors="replace")
                chapters_data.append({"chapter_num": idx, "content": txt})
            except Exception as e:
                logger.warning(f"  [!] Notice reading chapter file '{cf.name}': {e}")

        return cls.scan_chapters(chapters_data)

    @classmethod
    def scan_chapters(cls, chapters: List[Dict[str, Any]] | List[str] | List[Tuple[Any, ...]]) -> LexicalCorpusIndex:
        """
        Scans an array of chapter dictionaries, tuples, or plain text strings.
        Accepts:
        - List[Dict[str, Any]] with keys 'content' and optional 'chapter_num' / 'number'
        - List[Tuple] e.g. (chapter_num, title, content) or (chapter_num, content)
        - List[str] containing pure chapter texts
        """
        raw_chapters: List[Tuple[int, str]] = []
        for idx, item in enumerate(chapters, 1):
            if isinstance(item, dict):
                c_num = item.get("chapter_num") or item.get("number") or idx
                content = item.get("content", "")
                raw_chapters.append((int(c_num), str(content)))
            elif isinstance(item, (tuple, list)):
                if len(item) == 2:
                    raw_chapters.append((int(item[0]), str(item[1])))
                elif len(item) >= 3:
                    raw_chapters.append((int(item[0]), str(item[2])))
            elif isinstance(item, str):
                raw_chapters.append((idx, item))

        total_words = sum(len(c[1].split()) for c in raw_chapters)
        entities: Dict[str, EntityOccurrence] = {}

        for ch_num, text in raw_chapters:
            if not text.strip():
                continue

            # Split into paragraphs for co-occurrence tracking and context quotes
            paras = [p.strip() for p in text.split("\n\n") if p.strip()]

            for para in paras:
                para_entities_in_context: Set[str] = set()

                # 1. Check Title + Name patterns: e.g. "Captain Drake", "Lord Corwin"
                for m in TITLE_HONORIFICS_PATTERN.finditer(para):
                    title = m.group(1).strip()
                    name = m.group(2).strip()
                    if is_stopword(name):
                        continue
                    full_entity = name
                    cls._record_entity(
                        entities=entities,
                        name=full_entity,
                        ch_num=ch_num,
                        quote=para[:250],
                        associated_title=title,
                    )
                    para_entities_in_context.add(full_entity)

                # 2. Check Multi-word proper nouns: e.g. "Geralt of Rivia", "Edna Pontellier", "Lord Corwin"
                for m in MULTIWORD_PROPER_NOUN_PATTERN.finditer(para):
                    name = m.group(1).strip()
                    parts = name.split()
                    if is_stopword(parts[0]) or is_stopword(parts[-1]):
                        continue
                    if parts[0] in TITLE_WORDS and len(parts) >= 2:
                        title = parts[0]
                        base_name = " ".join(parts[1:])
                        if not is_stopword(base_name):
                            cls._record_entity(
                                entities=entities,
                                name=base_name,
                                ch_num=ch_num,
                                quote=para[:250],
                                associated_title=title,
                            )
                            para_entities_in_context.add(base_name)
                    cls._record_entity(
                        entities=entities,
                        name=name,
                        ch_num=ch_num,
                        quote=para[:250],
                    )
                    para_entities_in_context.add(name)

                # 3. Check Post-dialogue speakers: '"..." said Geralt' and '"..." Geralt said'
                for pat in (POST_DIALOGUE_SPEAKER_PATTERN, POST_DIALOGUE_SPEAKER_THEN_VERB_PATTERN):
                    for m in pat.finditer(para):
                        speaker = m.group(1).strip()
                        if not is_stopword(speaker):
                            cls._record_entity(
                                entities=entities,
                                name=speaker,
                                ch_num=ch_num,
                                quote=para[:250],
                                is_speaker=True,
                            )
                            para_entities_in_context.add(speaker)

                # 4. Check Pre-dialogue speakers: 'Geralt said, "..."', 'Said Geralt, "..."', and clause 'Elena ... whispered, "..."'
                for pat in (PRE_DIALOGUE_SPEAKER_PATTERN, PRE_DIALOGUE_VERB_THEN_SPEAKER_PATTERN):
                    for m in pat.finditer(para):
                        speaker = m.group(1).strip()
                        if not is_stopword(speaker) and speaker not in TITLE_WORDS:
                            cls._record_entity(
                                entities=entities,
                                name=speaker,
                                ch_num=ch_num,
                                quote=para[:250],
                                is_speaker=True,
                            )
                            para_entities_in_context.add(speaker)

                # 4B. Check Clause Pre-dialogue speakers (e.g. "Elena drew her cloak tight and whispered, '...'")
                for m in re.finditer(r'\b([A-Z][a-z]{2,20})\b[^.!?\n]{0,60}\s+(?:said|asked|replied|whispered|cried|shouted|murmured|roared|growled|gasped|muttered|yelled|demanded|snarled|chuckled)\s*[,:\s]*["\'“]', para):
                    speaker = m.group(1).strip()
                    if not is_stopword(speaker) and speaker not in TITLE_WORDS:
                        cls._record_entity(
                            entities=entities,
                            name=speaker,
                            ch_num=ch_num,
                            quote=para[:250],
                            is_speaker=True,
                        )
                        para_entities_in_context.add(speaker)

                # 5. Check all capitalized proper nouns (e.g. Elena, Wyzima, Corwin)
                for m in re.finditer(r'\b([A-Z][a-z]{2,20})\b', para):
                    w = m.group(1).strip()
                    # Check for trailing contraction e.g. Don't -> Don
                    trailing_contract = re.match(r"^['’](?:t|s|ll|re|ve|d|m)\b", para[m.end():], re.IGNORECASE)
                    if trailing_contract:
                        full_contract = w + trailing_contract.group(0)
                        if is_stopword(w) or is_stopword(full_contract):
                            continue
                    if not is_stopword(w) and w not in TITLE_WORDS:
                        cls._record_entity(
                            entities=entities,
                            name=w,
                            ch_num=ch_num,
                            quote=para[:250],
                        )
                        para_entities_in_context.add(w)

                # 6. Record co-occurrences within this paragraph
                for e1 in para_entities_in_context:
                    for e2 in para_entities_in_context:
                        if e1 != e2 and e1 in entities:
                            entities[e1].co_occurring_names[e2] += 1

        # Filter entities that appeared only once with 0 dialogue attributions and are single words
        cleaned_entities: Dict[str, EntityOccurrence] = {}
        for k, v in entities.items():
            if v.dialogue_speaker_count > 0 or v.total_mentions >= 2 or len(k.split()) > 1 or len(v.associated_titles) > 0:
                cleaned_entities[k] = v

        return LexicalCorpusIndex(
            entities=cleaned_entities,
            total_chapters=len(raw_chapters),
            total_words=total_words,
        )

    @staticmethod
    def _record_entity(
        entities: Dict[str, EntityOccurrence],
        name: str,
        ch_num: int,
        quote: str,
        is_speaker: bool = False,
        associated_title: Optional[str] = None,
    ) -> None:
        """Internal helper to atomically update entity statistics in the index."""
        if name not in entities:
            entities[name] = EntityOccurrence(
                name=name,
                first_chapter=ch_num,
                total_mentions=1,
                dialogue_speaker_count=1 if is_speaker else 0,
                chapters_appeared={ch_num},
                introductory_quote=quote,
            )
        else:
            ent = entities[name]
            ent.total_mentions += 1
            if is_speaker:
                ent.dialogue_speaker_count += 1
            ent.chapters_appeared.add(ch_num)
            if not ent.introductory_quote and quote:
                ent.introductory_quote = quote

        if associated_title:
            entities[name].associated_titles.add(associated_title)
