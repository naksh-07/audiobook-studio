import os
import re
import subprocess
import shutil
from typing import Optional

def get_ffmpeg() -> str:
    from audiobook_factory.tts.constants import get_ffmpeg as _get_ffmpeg
    return _get_ffmpeg()

def test_filter_graph(filter_complex: str, has_foley: bool = True) -> str:
    """Tool: Tests an FFmpeg filter graph for syntax errors using dummy audio."""
    ffmpeg = get_ffmpeg()
    if not (os.path.exists(ffmpeg) or shutil.which(ffmpeg)):
        return "ERROR: ffmpeg executable not found."

    # Validate stream references against available inputs
    if not has_foley and "[3:a]" in filter_complex:
        return "ERROR: Stream [3:a] does not exist because there are no Foley SFX cues in this chapter. Only [0:a] (Voice), [1:a] (BGM), and [2:a] (Ambience) are available."

    # Simulate inputs: voc_dry, bgm, amb_bed, (optional) fol_bus
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",  # 0:a Voice
        "-f", "lavfi", "-i", "sine=frequency=400:duration=1",   # 1:a BGM
        "-f", "lavfi", "-i", "sine=frequency=300:duration=1",   # 2:a Ambience
    ]
    if has_foley or "[3:a]" in filter_complex:
        cmd.extend(["-f", "lavfi", "-i", "sine=frequency=200:duration=1"])  # 3:a Foley

    map_args = []
    if "[out]" in filter_complex:
        map_args = ["-map", "[out]"]
    else:
        labels = re.findall(r'\[([a-zA-Z0-9_]+)\]', filter_complex)
        if labels and labels[-1] not in ('0', '1', '2', '3', '0:a', '1:a', '2:a', '3:a'):
            map_args = ["-map", f"[{labels[-1]}]"]

    cmd.extend([
        "-filter_complex", filter_complex,
        *map_args,
        "-f", "null", "-"
    ])
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30.0)
        if res.returncode == 0:
            return "SUCCESS: Filter graph syntax is valid."
        else:
            lines = [l for l in res.stderr.strip().split('\n') if l.strip()]
            return "ERROR: " + "\n".join(lines[-8:])
    except Exception as e:
        return f"ERROR: {str(e)}"

# Define Gemini Function Calling Schema
TOOLS = [{
    "functionDeclarations": [
        {
            "name": "test_filter_graph",
            "description": "Tests an FFmpeg filter_complex string for syntax errors before finalizing it. Always test your graph if you use complex routing.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "filter_complex": {
                        "type": "STRING",
                        "description": "The FFmpeg filter_complex string to test. E.g. '[0:a][1:a]amix=inputs=2[out]'"
                    }
                },
                "required": ["filter_complex"]
            }
        }
    ]
}]

def build_ffmpeg_filter_graph_via_agent(
    soundscape_plan: dict = None, 
    cue_sheet: dict = None, 
    vocal_dur: float = 0.0, 
    has_foley: bool = False
) -> Optional[str]:
    """
    [DISABLED BY PURE VOCALS-ONLY INVARIANT]
    LLM audio engineer agent is disabled. All vocal mastering is handled by Room 5.
    """
    # ponytail: root deadbolt - LLM audio mixing and BGM/SFX agents disabled
    raise RuntimeError(
        "build_ffmpeg_filter_graph_via_agent is disabled. BGM/SFX mixing is permanently decoupled "
        "under Pure Vocals-Only Mandate, and all LLM calls are restricted to Antigravity."
    )


def build_manifest_mastering_filter_graph_via_agent(
    manifest_data: dict,
    vocal_dur: float,
    has_foley: bool = True,
    has_music: bool = True,
    has_ambience: bool = True,
) -> str:
    """
    [DISABLED BY PURE VOCALS-ONLY INVARIANT]
    Mastering filter graph via LLM agent is disabled. All vocal mastering is handled by Room 5.
    """
    # ponytail: root deadbolt - LLM audio mixing and stem agents disabled
    raise RuntimeError(
        "build_manifest_mastering_filter_graph_via_agent is disabled. BGM/SFX mixing is permanently decoupled "
        "under Pure Vocals-Only Mandate, and all LLM calls are restricted to Antigravity."
    )
