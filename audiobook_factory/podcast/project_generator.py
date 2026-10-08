#!/usr/bin/env python3
"""
Audiobook Factory - Dedicated Podcast Engine: Project Batch Generator.
Processes chapters in a project, coordinates Dramaturgy AST generation,
and outputs 2-Host podcast JSON scripts and PodcastEpisodePlan artifacts.
"""

from __future__ import annotations
import re
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from audiobook_factory.dramaturgy.scene_analyzer import SceneAnalyzer
from audiobook_factory.dramaturgy.beat_planner import BeatPlanner
from audiobook_factory.dramaturgy.contracts import DramaticPlan
from audiobook_factory.podcast.contracts import PodcastEpisodePlan

logger = logging.getLogger("AudiobookFactory")


def generate_project_podcasts(
    project_dir: Path,
    use_hindi: bool = True,
    overwrite: bool = False,
    chapters: Optional[List[int]] = None,
    model: Optional[str] = None,
) -> Path:
    """Generates 2-Host conversational podcast episodes for all chapters in a project."""
    project_dir = Path(project_dir).resolve()
    input_dir = project_dir / ("translation" if use_hindi else "extracted")
    podcasts_dir = project_dir / "podcasts"
    podcasts_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir = project_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    target_files = sorted(input_dir.glob("*.md"))
    if chapters:
        target_files = [
            tf for tf in target_files
            if any(f"_{ch:03d}" in tf.stem or tf.stem.endswith(f"_{ch}") or tf.stem == f"chapter_{ch:03d}" or tf.stem == f"chapter_{ch}" for ch in chapters)
        ]
    if not target_files:
        raise FileNotFoundError(f"No markdown chapters found in {input_dir}")

    # Load character roster / glossary if available
    roster = None
    roster_file = project_dir / "character_roster.json"
    if roster_file.exists():
        try:
            with open(roster_file, "r", encoding="utf-8") as f:
                roster = json.load(f)
        except Exception:
            pass

    # Load BookBible & MemoryStore if available
    bible = None
    memory_store = None
    try:
        from audiobook_factory.translation.book_bible import BookBible
        from audiobook_factory.translation.memory import MemoryStore
        bible = BookBible.load_from_project(project_dir)
        memory_store = MemoryStore.load(MemoryStore.default_store_path(project_dir), book_bible=bible)
    except Exception:
        pass

    from audiobook_factory.adapters.podcast import PodcastAdapter
    adapter = PodcastAdapter(model=model)

    print(f"[*] Generating 2-Host podcasts for {len(target_files)} chapters (Language: {'Hindi' if use_hindi else 'English'})...")

    for seq_idx, chap_file in enumerate(target_files, 1):
        m_ch = re.search(r"chapter_(\d+)", chap_file.stem, re.IGNORECASE)
        real_ch = int(m_ch.group(1)) if m_ch else seq_idx
        plan_file = podcasts_dir / f"{chap_file.stem}_podcast_plan.json"
        script_file = scripts_dir / f"{chap_file.stem}_podcast_script.json"

        if not overwrite and plan_file.exists() and plan_file.stat().st_size > 50:
            print(f"[-] Podcast plan already exists: {plan_file.name} (Skipping)")
            continue

        with open(chap_file, "r", encoding="utf-8") as f:
            content = f.read()

        mem_ctx = None
        if memory_store is not None:
            try:
                from audiobook_factory.translation.memory import MemoryRetriever
                mem_ctx = MemoryRetriever.retrieve_for_scene(
                    store=memory_store,
                    book_bible=bible,
                    chapter=real_ch,
                    scene_id=chap_file.stem,
                    scene_text=content,
                )
            except Exception:
                mem_ctx = None

        # 1. Synthesize Shared Understanding & Dramaturgy Core
        known_chars = list(bible.characters.keys()) if bible and bible.characters else None
        scenes = SceneAnalyzer.segment_and_analyze_scenes(
            chapter_text=content,
            chapter_num=real_ch,
            chapter_title=f"Chapter {real_ch}",
            known_characters=known_chars,
            memory_context=mem_ctx,
        )
        scenes = BeatPlanner.plan_chapter_beats(
            chapter_text=content,
            scenes=scenes,
            known_characters=known_chars,
            memory_context=mem_ctx,
        )
        dramatic_plan = DramaticPlan(
            chapter_id=chap_file.stem,
            chapter_num=real_ch,
            scenes=scenes,
            total_beats=sum(len(s.beats) for s in scenes),
        )

        # 2. Adapt to 2-Host Podcast
        standard_segments, episode_plan = adapter.adapt(
            chapter_text=content,
            dramatic_plan=dramatic_plan,
            character_roster=roster,
            memory_context=mem_ctx,
            is_hindi=use_hindi,
            chapter_num=real_ch,
            chapter_id=chap_file.stem,
            return_plan=True,
        )

        # Save artifacts
        episode_plan.save_to_file(plan_file)
        with open(script_file, "w", encoding="utf-8") as f:
            json.dump(standard_segments, f, ensure_ascii=False, indent=2)

        print(f"[+] Built podcast episode for {chap_file.name} -> {len(standard_segments)} dialogue turns (~{episode_plan.total_duration_estimate_sec/60.0:.1f} mins)")

    print(f"[DONE] All podcast episodes built -> {podcasts_dir}")
    return podcasts_dir
