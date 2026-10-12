#!/usr/bin/env python3
"""
Audiobook Factory - Room 1: Pre-Production Supervisor.
Coordinates the Pre-Production Studio agents to establish locked novel master state:
1. book_bible.json: Authoritative lore, characters, locations, and relationships.
2. sonic_bible.json: Acoustic DNA, room impulse reverb targets, and signature foley palettes.
3. cast_lock.json: Collision-free voice actor assignments locked for the entire novel.

Guarantees one-time master execution per novel with zero voice drift across chapters.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from audiobook_factory.metadata.book_bible import (
    BookBible,
    BookEntity,
    EpistemicProvenance,
)
from audiobook_factory.metadata.state_maintainer import NovelStateMaintainer
from audiobook_factory.character_caster import CharacterCaster
from .novel_deepsearch import NovelDeepSearchEngine, DeepSearchNovelDossier
from .book_dna_agent import BookDNAAgent
from .dramatis_personae_agent import DramatisPersonaeAgent
from .sonic_world_architect import SonicWorldArchitect
from .vocal_acoustic_director import VocalAcousticDirector, VocalSpacesManifest
from .phonetic_lexicon_dramaturge import PhoneticLexiconDramaturge
from .lexical_scanner import LexicalCorpusScanner, LexicalCorpusIndex

logger = logging.getLogger("AudiobookFactory")


class PreProductionSupervisor:
    """Room 1 Showrunner: Coordinates full-novel lore, acoustic DNA, and voice locking."""

    def __init__(self, model: Optional[str] = None):
        self.model = model
        self.deepsearch = NovelDeepSearchEngine(model=model)
        self.book_dna_agent = BookDNAAgent(model=model)
        self.dramatis_personae_agent = DramatisPersonaeAgent(model=model)
        self.sonic_architect = SonicWorldArchitect(model=model)
        self.vocal_director = VocalAcousticDirector(model=model)
        self.lexicon_dramaturge = PhoneticLexiconDramaturge(model=model)

    def execute_preproduction(
        self,
        project_dir: Path | str,
        force: bool = False,
        call_llm_fn: Optional[Callable[..., Any]] = None,
    ) -> Dict[str, Any]:
        """Executes one-time pre-production master pass for the novel."""
        p_dir = Path(project_dir).resolve()
        book_dna_path = p_dir / "book_dna.json"
        playbook_path = p_dir / "production_playbook.json"
        book_bible_path = p_dir / "book_bible.json"
        sonic_bible_path = p_dir / "sonic_bible.json"
        vocal_spaces_path = p_dir / "vocal_spaces.json"
        cast_lock_path = p_dir / "cast_lock.json"
        meta_path = p_dir / "metadata.json"

        # Check existing master state
        if not force and book_dna_path.exists() and playbook_path.exists() and book_bible_path.exists() and (vocal_spaces_path.exists() or sonic_bible_path.exists()) and cast_lock_path.exists():
            logger.info(f"[*] PreProductionSupervisor: Master novel state already locked for {p_dir.name}. Skipping.")
            return {
                "status": "CACHED_LOCKED",
                "book_dna": str(book_dna_path),
                "production_playbook": str(playbook_path),
                "book_bible": str(book_bible_path),
                "sonic_bible": str(sonic_bible_path),
                "vocal_spaces": str(vocal_spaces_path),
                "cast_lock": str(cast_lock_path),
            }


        logger.info(f"[*] PreProductionSupervisor: Commencing One-Time Pre-Production Master Room for '{p_dir.name}'...")

        book_metadata: Dict[str, Any] = {}
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    book_metadata = json.load(f)
            except Exception:
                pass

        if not book_metadata.get("title"):
            book_metadata["title"] = p_dir.name.replace("_", " ").title()
        book_metadata.setdefault("project_slug", p_dir.name)

        # 0. Deterministic Full-Corpus Lexical Sweep (100% Chapter Coverage, 0 Tokens)
        logger.info("  [Room 1 Step 0/5] Scanning full novel corpus with deterministic LexicalCorpusScanner...")
        lexical_index = LexicalCorpusScanner.scan_project_dir(p_dir)
        logger.info(
            f"  [+] LexicalCorpusScanner complete: {lexical_index.total_words} words across "
            f"{lexical_index.total_chapters} chapters, {len(lexical_index.entities)} unique candidate entities."
        )

        # Gather sample chapters across the novel (beginning, middle, climax, end)
        search_dirs = [p_dir / "extracted", p_dir / "chapters", p_dir / "translation"]
        chapter_files = []
        for sdir in search_dirs:
            if sdir.exists():
                chapter_files = sorted(sdir.glob("chapter_*.md"))
                if chapter_files:
                    break

        sample_passages: list[str] = []
        if chapter_files:
            step = max(1, len(chapter_files) // 8)
            selected_files = chapter_files[::step][:8]
            for cf in selected_files:
                try:
                    txt = cf.read_text(encoding="utf-8")
                    sample_passages.append(txt[:4000])
                except Exception:
                    pass

        combined_sample = "\n\n--- NEXT CHAPTER ---\n\n".join(sample_passages)
        if not combined_sample.strip():
            combined_sample = f"Novel title: {book_metadata.get('title')}"

        # 0A. Canonical Novel DeepSearch Reconnaissance with Bidirectional Grounding Gate
        dossier_path = p_dir / "book_dossier.json"
        dossier: Optional[DeepSearchNovelDossier] = None
        if dossier_path.exists():
            try:
                with open(dossier_path, "r", encoding="utf-8") as f:
                    dossier = DeepSearchNovelDossier.model_validate_json(f.read())
                if dossier and dossier.characters and len(dossier.characters) > 0 and dossier.characters[0].english_name != "Protagonist":
                    logger.info(f"  [Room 1 Step 0A/5] Canonical Novel DeepSearch dossier verified on disk ({len(dossier.characters)} characters). Reusing existing research.")
                else:
                    dossier = None
            except Exception as e:
                logger.warning(f"  [Room 1 Step 0A/5] Existing dossier unreadable ({e}), re-running web reconnaissance...")
                dossier = None

        if dossier is None:
            logger.info("  [Room 1 Step 0A/5] NovelDeepSearch conducting multi-angle web reconnaissance...")
            dossier = self.deepsearch.conduct_deepsearch(
                title=book_metadata.get("title", ""),
                author=book_metadata.get("author", ""),
                sample_text=combined_sample,
                project_slug=p_dir.name,
                call_llm_fn=call_llm_fn,
                lexical_index=lexical_index,
            )
            with open(dossier_path, "w", encoding="utf-8") as f:
                json.dump(dossier.model_dump(), f, ensure_ascii=False, indent=2)

        # 0B. Universal Literary DNA & Register Profiling (Novel-Agnostic)
        book_dna_data = None
        if book_dna_path.exists() and not force:
            try:
                with open(book_dna_path, "r", encoding="utf-8") as f:
                    book_dna_data = json.load(f)
                if book_dna_data.get("literary_tradition"):
                    logger.info("  [Room 1 Step 0B/5] Existing book_dna.json verified on disk. Reusing.")
                else:
                    book_dna_data = None
            except Exception:
                book_dna_data = None
            except Exception:
                book_dna_data = None

        if book_dna_data is None:
            logger.info("  [Room 1 Step 0B/5] BookDNAAgent profiling universal literary DNA & register...")
            book_dna_data = self.book_dna_agent.analyze_book_dna(
                novel_text_sample=combined_sample,
                book_metadata=book_metadata,
                call_llm_fn=call_llm_fn,
                enable_web_research=(dossier is None),
            )
        # Synchronize with DeepSearch canonical findings
        # Synchronize with DeepSearch canonical findings
        if dossier:
            d_lit = getattr(dossier, "literary_dna", None) or (dossier.get("literary_dna") if isinstance(dossier, dict) else None)
            d_acoustics = getattr(dossier, "world_acoustics", None) or (dossier.get("world_acoustics") if isinstance(dossier, dict) else None)
            d_ling = getattr(dossier, "linguistic_dialect", None) or (dossier.get("linguistic_dialect") if isinstance(dossier, dict) else None)
            d_music = getattr(dossier, "musical_tradition", None) or (dossier.get("musical_tradition") if isinstance(dossier, dict) else None)

            if d_lit:
                trad = getattr(d_lit, "tradition", None) or (d_lit.get("tradition") if isinstance(d_lit, dict) else None)
                if trad:
                    book_dna_data["literary_tradition"] = trad
                tier = getattr(d_lit, "source_fidelity_tier", None) or (d_lit.get("source_fidelity_tier") if isinstance(d_lit, dict) else None)
                if tier:
                    book_dna_data["source_fidelity_tier"] = tier
                tone = getattr(d_lit, "narrative_tone", None) or (d_lit.get("narrative_tone") if isinstance(d_lit, dict) else None)
                if tone:
                    book_dna_data["world_atmosphere_summary"] = tone
                era = getattr(d_lit, "historical_era", None) or (d_lit.get("historical_era") if isinstance(d_lit, dict) else None)
                if era:
                    book_dna_data["historical_era"] = era

            if d_acoustics:
                banned = getattr(d_acoustics, "banned_anachronisms", None) or (d_acoustics.get("banned_anachronisms") if isinstance(d_acoustics, dict) else None)
                if banned:
                    book_dna_data["banned_anachronisms"] = banned

            if d_ling:
                loans = getattr(d_ling, "acceptable_loanwords", None) or (d_ling.get("acceptable_loanwords") if isinstance(d_ling, dict) else None)
                if loans:
                    book_dna_data["acceptable_loanwords"] = loans
                reg = getattr(d_ling, "recommended_hindustani_register", None) or (d_ling.get("recommended_hindustani_register") if isinstance(d_ling, dict) else None)
                if reg:
                    book_dna_data["regional_dialect_cadence"] = reg

            if d_music:
                insts = getattr(d_music, "signature_instruments", None) or (d_music.get("signature_instruments") if isinstance(d_music, dict) else None)
                if insts:
                    book_dna_data["musical_instruments"] = insts

        # 0C. Novel Production Playbook Synthesis
        playbook = None
        if playbook_path.exists() and not force:
            try:
                from audiobook_factory.contracts.playbook import ProductionPlaybook
                playbook = ProductionPlaybook.model_validate_json(playbook_path.read_text(encoding="utf-8"))
                logger.info("  [Room 1 Step 0C/5] Existing production_playbook.json verified on disk. Reusing.")
            except Exception:
                playbook = None

        if playbook is None:
            logger.info("  [Room 1 Step 0C/5] ProductionPlaybookSynthesizer synthesizing tailored playbook...")
            from audiobook_factory.preproduction.playbook_synthesizer import ProductionPlaybookSynthesizer
            syn = ProductionPlaybookSynthesizer(model=self.model)
            d_dump = dossier.model_dump() if hasattr(dossier, "model_dump") else (dossier if isinstance(dossier, dict) else None)
            playbook = syn.synthesize_playbook(
                book_dna=book_dna_data,
                book_dossier=d_dump,
                book_metadata=book_metadata,
                call_llm_fn=call_llm_fn,
            )
            import uuid
            tmp_pb_path = p_dir / f"production_playbook.tmp.{os.getpid()}_{uuid.uuid4().hex[:6]}"
            with open(tmp_pb_path, "w", encoding="utf-8") as f:
                json.dump(playbook.model_dump(), f, ensure_ascii=False, indent=2)
            os.replace(tmp_pb_path, playbook_path)

        # 1. Dramatis Personae Extraction (Guided by Book DNA & DeepSearch)
        logger.info("  [Room 1 Step 1/5] DramatisPersonaeAgent extracting character dossiers...")

        raw_chars = self.dramatis_personae_agent.extract_dramatis_personae(
            novel_text_sample=combined_sample,
            book_metadata=book_metadata,
            book_dna=book_dna_data,
            call_llm_fn=call_llm_fn,
        )

        # Seed characters_list with DeepSearch canonical characters so verified Devanagari spellings take precedence
        characters_list: list[Dict[str, Any]] = []
        known_names = set()
        if dossier and dossier.characters:
            for d_char in dossier.characters:
                c_name = d_char.english_name.strip()
                if c_name and c_name.lower() != "protagonist":
                    characters_list.append({
                        "english_name": c_name,
                        "hindi_name": d_char.hindi_name,
                        "gender": d_char.gender,
                        "aliases": d_char.aliases,
                        "prominence": d_char.role_prominence,
                        "vocal_archetype": d_char.vocal_weight,
                        "sociolect_trait": d_char.occupation_status or "NEUTRAL",
                        "recommended_pronoun_level": "aap" if d_char.age_group == "elder" else "tum",
                        "speech_quirks": "",
                    })
                    known_names.add(c_name.lower())
                    for a in d_char.aliases:
                        known_names.add(a.lower())

        # Append novel-text discovered characters not already covered by canonical dossier
        for c in raw_chars:
            if isinstance(c, dict) and c.get("english_name"):
                name = c["english_name"].strip()
                if name.lower() not in known_names and name.lower() not in ("protagonist", "narrator"):
                    characters_list.append(c)
                    known_names.add(name.lower())

        # Append high-frequency speaking characters from full-text lexical scanner
        if lexical_index:
            for top_ent in lexical_index.get_top_speaking_characters(40):
                ent_name = top_ent.name.strip()
                if ent_name.lower() not in known_names and ent_name.lower() not in ("protagonist", "narrator"):
                    if top_ent.dialogue_speaker_count >= 1 or top_ent.total_mentions >= 3:
                        characters_list.append({
                            "english_name": ent_name,
                            "hindi_name": ent_name,
                            "gender": "neutral",
                            "aliases": sorted(list(top_ent.associated_titles)),
                            "prominence": "lead" if top_ent.dialogue_speaker_count >= 10 else "major" if top_ent.dialogue_speaker_count >= 3 else "minor",
                            "vocal_archetype": "authoritative",
                            "sociolect_trait": "NEUTRAL",
                            "recommended_pronoun_level": "tum",
                            "speech_quirks": "",
                        })
                        known_names.add(ent_name.lower())

        # 2. Vocal Acoustic Architecture & Room Impulse Spaces (Vocals-Only)
        vocal_manifest: Optional[VocalSpacesManifest] = None
        if vocal_spaces_path.exists() and not force:
            try:
                with open(vocal_spaces_path, "r", encoding="utf-8") as vf:
                    vocal_manifest = VocalSpacesManifest.model_validate_json(vf.read())
                if vocal_manifest and vocal_manifest.spaces:
                    logger.info("  [Room 1 Step 2/5] Existing vocal_spaces.json verified on disk. Reusing.")
                else:
                    vocal_manifest = None
            except Exception:
                vocal_manifest = None

        if vocal_manifest is None:
            logger.info("  [Room 1 Step 2/5] VocalAcousticDirector synthesizing vocal room acoustics...")
            vocal_manifest = self.vocal_director.design_vocal_spaces(
                novel_text_sample=combined_sample,
                book_metadata=book_metadata,
                call_llm_fn=call_llm_fn,
            )

        # 3. Phonetic Lexicon Extraction
        logger.info("  [Room 1 Step 3/5] PhoneticLexiconDramaturge extracting world lexicon...")
        lexicon_data = self.lexicon_dramaturge.extract_lexicon_and_phonetics(
            novel_text_sample=combined_sample,
            book_metadata=book_metadata,
            call_llm_fn=call_llm_fn,
        )

        # 4. Assemble BookBible in memory with Epistemic Provenance
        bible = BookBible.load_from_project(p_dir)
        bible.book_title = book_metadata.get("title", bible.book_title)
        bible.author = book_metadata.get("author", bible.author)

        for c_dict in characters_list:
            if isinstance(c_dict, dict) and c_dict.get("english_name"):
                eng_name = c_dict["english_name"]
                c_aliases = c_dict.get("aliases", [])
                c_mentions = lexical_index.get_mention_count(eng_name, c_aliases) if lexical_index else 1
                c_first_ch = lexical_index.get_first_chapter(eng_name) if lexical_index else 1
                c_quote = lexical_index.get_intro_sentence(eng_name) if lexical_index else ""

                prov_origin = "WEB_VERIFIED" if (dossier and any(dc.english_name.lower() == eng_name.lower() for dc in dossier.characters)) else "CORPUS_EXTRACTED"
                prov = EpistemicProvenance(
                    origin=prov_origin,
                    first_chapter=c_first_ch,
                    corpus_mention_count=c_mentions,
                    evidence_quote=c_quote,
                )

                entity = BookEntity(
                    canonical_name=eng_name,
                    english_name=eng_name,
                    hindi_name=c_dict.get("hindi_name", "") or eng_name,
                    gender=c_dict.get("gender", "neutral") or "neutral",
                    aliases=c_aliases,
                    sociolect_archetype=c_dict.get("sociolect_trait") or "NEUTRAL",
                    speech_quirks=c_dict.get("speech_quirks", "") or "",
                    default_honorific_level=c_dict.get("recommended_pronoun_level", "tum") or "tum",
                    provenance=prov,
                )
                bible.characters[eng_name] = entity

        if dossier and hasattr(dossier, "world_lore_entities") and dossier.world_lore_entities:
            bible.locations.update(dossier.world_lore_entities.get("locations", {}))
            bible.organizations.update(dossier.world_lore_entities.get("organizations", {}))
            bible.creatures.update(dossier.world_lore_entities.get("creatures", {}))
            bible.titles.update(dossier.world_lore_entities.get("titles", {}))
            bible.terminology.update(dossier.world_lore_entities.get("terminology", {}))

        bible.locations.update(lexicon_data.get("locations", {}))
        bible.organizations.update(lexicon_data.get("organizations", {}))
        bible.creatures.update(lexicon_data.get("creatures", {}))
        bible.objects.update(lexicon_data.get("objects", {}))
        bible.terminology.update(lexicon_data.get("terminology", {}))

        # 5. Allocate Voice Cast via CharacterCaster (NR-GATE-03 >=4% pitch separation)
        logger.info("  [Room 1 Step 4/5] Allocating non-colliding voice cast via CharacterCaster...")
        roster_chars = [
            {
                "name": c.english_name,
                "gender": c.gender or "male",
                "aliases": c.aliases,
                "archetype": c.sociolect_trait or "",
            }
            for c in bible.characters.values()
        ]
        if not roster_chars:
            roster_chars = [
                {"name": c.get("english_name"), "gender": c.get("gender", "male")}
                for c in characters_list if isinstance(c, dict) and c.get("english_name")
            ]
        roster, vreg, cast_lock = CharacterCaster._build_cast_allocation(
            project_id=f"proj-{p_dir.name}",
            raw_characters=roster_chars,
            use_hindi=True,
        )

        # 6. Commit Master Pre-Production State atomically via NovelStateMaintainer (NR-GATE-06)
        logger.info("  [Room 1 Finalize] Atomically committing master preproduction state via NovelStateMaintainer...")
        NovelStateMaintainer.commit_master_preproduction(
            project_dir=p_dir,
            book_metadata=book_metadata,
            book_dna=book_dna_data,
            book_bible=bible,
            vocal_spaces=vocal_manifest,
            roster=roster,
            voice_registry=vreg,
            cast_lock=cast_lock,
        )

        try:
            bible.sync_pronunciation_lexicon(p_dir)
        except Exception as e:
            logger.warning(f"  [!] Lexicon sync notice: {e}")

        logger.info(f"[+] PreProductionSupervisor: Novel master state locked successfully in {p_dir.name}.")
        return {
            "status": "MASTER_LOCKED",
            "characters_count": len(bible.characters),
            "locations_count": len(bible.locations),
            "book_dna": str(book_dna_path),
            "production_playbook": str(playbook_path),
            "book_bible": str(book_bible_path),
            "sonic_bible": str(sonic_bible_path),
            "vocal_spaces": str(vocal_spaces_path),
            "cast_lock": str(cast_lock_path),
        }



def run_preproduction(project_dir: Path | str, force: bool = False, model: Optional[str] = None) -> Dict[str, Any]:
    """Convenience helper to run one-time pre-production master pass."""
    supervisor = PreProductionSupervisor(model=model)
    return supervisor.execute_preproduction(project_dir=project_dir, force=force)
