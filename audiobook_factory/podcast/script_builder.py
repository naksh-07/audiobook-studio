#!/usr/bin/env python3
"""
Audiobook Studio - Dual-Host Podcast Script Builder (NotebookLM-Style).
Converts CanonicalBook AST into a dynamic, multi-turn conversational podcast
script optimized for Room 4 Gemini Flash TTS synthesis and 4D acoustic formants.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional

from audiobook_factory.extraction.contracts import (
    CanonicalBook,
    CanonicalChapter,
    CanonicalBlock,
)
from audiobook_factory.podcast.contracts import (
    PodcastScript,
    PodcastSegment,
    HostProfile,
)
from audiobook_factory.podcast.verbalizer import (
    MathVerbalizer,
    TableVerbalizer,
    AbstractCalloutVerbalizer,
)


class PodcastScriptBuilder:
    """
    Builds conversational dual-host podcast scripts from ingested CanonicalBook ASTs.
    """

    DEFAULT_HOSTS = [
        HostProfile(
            id="Host_A",
            name="Dr. Vance",
            role="lead_explainer",
            default_voice="Charon",
            acting_style="calm, steady, articulate, authoritative research delivery",
            formant_preset="lead_narrator",
        ),
        HostProfile(
            id="Host_B",
            name="Maya",
            role="inquisitive_cohost",
            default_voice="Aoede",
            acting_style="engaging, curious, dynamic, conversational analyst delivery",
            formant_preset="expressive_female",
        ),
    ]

    def __init__(
        self,
        hosts: Optional[List[HostProfile]] = None,
        style: str = "conversational_podcast",
    ):
        self.hosts = hosts or self.DEFAULT_HOSTS
        self.style = style

    def build_from_book(self, book: CanonicalBook) -> PodcastScript:
        """
        Converts a CanonicalBook AST into a full dual-host PodcastScript.
        """
        host_a = self.hosts[0]
        host_b = self.hosts[1] if len(self.hosts) > 1 else self.hosts[0]

        segments: List[PodcastSegment] = []
        seg_idx = 0

        # Podcast Intro Opening
        seg_idx += 1
        intro_text = (
            f"Welcome to AI Research Deep-Dive. I'm {host_a.name}, and today we're breaking down "
            f"a compelling new paper titled: '{book.title}'."
        )
        segments.append(
            PodcastSegment(
                segment_id=f"seg-{seg_idx:04d}",
                speaker=host_a.id,
                character_name=host_a.name,
                text=intro_text,
                acting_directive="engaging, warm podcast host intro",
                source_block_type="intro",
                pause_after_ms=350,
            )
        )

        seg_idx += 1
        intro_reply = (
            f"Hey everyone! I'm {host_b.name}. This is a fascinating study because it tackles "
            f"real architectural bottlenecks in automated knowledge extraction and speech synthesis."
        )
        segments.append(
            PodcastSegment(
                segment_id=f"seg-{seg_idx:04d}",
                speaker=host_b.id,
                character_name=host_b.name,
                text=intro_reply,
                acting_directive="enthusiastic, curious co-host intro",
                source_block_type="intro",
                pause_after_ms=300,
            )
        )

        current_speaker = host_a

        for chapter in book.chapters:
            # Section Landmark announcement
            if chapter.title and chapter.title.lower() not in ("prologue", "prologue / introduction"):
                seg_idx += 1
                section_prompt = f"Let's dive into {chapter.title}."
                segments.append(
                    PodcastSegment(
                        segment_id=f"seg-{seg_idx:04d}",
                        speaker=current_speaker.id,
                        character_name=current_speaker.name,
                        text=section_prompt,
                        acting_directive="clear section transition",
                        source_block_type="heading",
                        pause_after_ms=250,
                    )
                )
                current_speaker = host_b if current_speaker == host_a else host_a

            for block in chapter.blocks:
                b_type = block.type
                norm_text = block.normalized_text.strip()
                if not norm_text:
                    continue

                if b_type == "abstract":
                    # Verbalize abstract
                    spoken_abstract = AbstractCalloutVerbalizer.verbalize_abstract(norm_text)
                    seg_idx += 1
                    segments.append(
                        PodcastSegment(
                            segment_id=f"seg-{seg_idx:04d}",
                            speaker=host_a.id,
                            character_name=host_a.name,
                            text=spoken_abstract,
                            acting_directive="focused, analytical delivery",
                            source_block_id=block.id,
                            source_block_type="abstract",
                            pause_after_ms=300,
                        )
                    )
                    current_speaker = host_b

                elif b_type == "equation":
                    # Verbalize LaTeX math equation
                    raw_latex = block.semantic_metadata.get("latex") or norm_text
                    spoken_math = MathVerbalizer.verbalize_latex(raw_latex)

                    seg_idx += 1
                    segments.append(
                        PodcastSegment(
                            segment_id=f"seg-{seg_idx:04d}",
                            speaker=host_a.id,
                            character_name=host_a.name,
                            text=f"Looking at the mathematical formulation, {spoken_math}.",
                            acting_directive="precise, articulate mathematical narration",
                            source_block_id=block.id,
                            source_block_type="equation",
                            pause_after_ms=350,
                        )
                    )

                    # Host B reaction/intuition
                    seg_idx += 1
                    segments.append(
                        PodcastSegment(
                            segment_id=f"seg-{seg_idx:04d}",
                            speaker=host_b.id,
                            character_name=host_b.name,
                            text="That formulation is crucial because it balances acoustic spectral loss with 4D formant alignment.",
                            acting_directive="insightful, conversational reaction",
                            source_block_id=block.id,
                            source_block_type="equation_discussion",
                            pause_after_ms=300,
                        )
                    )
                    current_speaker = host_a

                elif b_type == "table":
                    # Verbalize Markdown table
                    table_insight = TableVerbalizer.verbalize_table(block.raw_text, title=chapter.title)

                    seg_idx += 1
                    segments.append(
                        PodcastSegment(
                            segment_id=f"seg-{seg_idx:04d}",
                            speaker=host_b.id,
                            character_name=host_b.name,
                            text=table_insight,
                            acting_directive="engaging data analysis delivery",
                            source_block_id=block.id,
                            source_block_type="table",
                            pause_after_ms=350,
                        )
                    )
                    current_speaker = host_a

                elif b_type == "callout":
                    # Verbalize Callout note
                    callout_insight = AbstractCalloutVerbalizer.verbalize_callout(norm_text)

                    seg_idx += 1
                    segments.append(
                        PodcastSegment(
                            segment_id=f"seg-{seg_idx:04d}",
                            speaker=host_b.id,
                            character_name=host_b.name,
                            text=callout_insight,
                            acting_directive="emphatic, clear key takeaway",
                            source_block_id=block.id,
                            source_block_type="callout",
                            pause_after_ms=300,
                        )
                    )
                    current_speaker = host_a

                else:
                    # Standard paragraph prose: verbalize any inline math ($...$) and alternate between hosts
                    spoken_prose = MathVerbalizer.verbalize_inline_math(norm_text)
                    seg_idx += 1
                    segments.append(
                        PodcastSegment(
                            segment_id=f"seg-{seg_idx:04d}",
                            speaker=current_speaker.id,
                            character_name=current_speaker.name,
                            text=spoken_prose,
                            acting_directive="natural conversational delivery",
                            source_block_id=block.id,
                            source_block_type=b_type,
                            pause_after_ms=250,
                        )
                    )
                    current_speaker = host_b if current_speaker == host_a else host_a

        # Podcast Outro
        seg_idx += 1
        outro_a = f"That wraps up our deep-dive into {book.title}. Thanks for tuning in!"
        segments.append(
            PodcastSegment(
                segment_id=f"seg-{seg_idx:04d}",
                speaker=host_a.id,
                character_name=host_a.name,
                text=outro_a,
                acting_directive="warm podcast outro sign-off",
                source_block_type="outro",
                pause_after_ms=300,
            )
        )

        seg_idx += 1
        outro_b = "See you in the next episode. Keep exploring!"
        segments.append(
            PodcastSegment(
                segment_id=f"seg-{seg_idx:04d}",
                speaker=host_b.id,
                character_name=host_b.name,
                text=outro_b,
                acting_directive="upbeat co-host sign-off",
                source_block_type="outro",
                pause_after_ms=400,
            )
        )

        return PodcastScript(
            podcast_id=f"pod_{book.book_id}",
            title=book.title,
            source_document_id=book.book_id,
            hosts=self.hosts,
            segments=segments,
        )


def generate_podcast_script_from_file(
    input_file: Path | str,
    output_dir: Optional[Path | str] = None,
) -> PodcastScript:
    """
    Convenience function to ingest a document and generate a podcast script.
    """
    from audiobook_factory.extraction import ExtractionEngine

    in_path = Path(input_file).resolve()
    out_base = Path(output_dir).resolve() if output_dir else in_path.parent / "projects"

    book = ExtractionEngine.extract(in_path, out_base, force_gate=True)
    builder = PodcastScriptBuilder()
    script = builder.build_from_book(book)

    # Save podcast script to project directory
    proj_dir = out_base / book.book_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    script_path = proj_dir / "podcast_script.json"
    
    import json
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script.to_screenplay_json(), f, indent=2, ensure_ascii=False)

    return script
