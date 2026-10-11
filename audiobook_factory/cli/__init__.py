from __future__ import annotations

try:
    from audiobook_factory.cli.commands.pipeline import (
        cmd_extract,
        cmd_translate,
        cmd_script,
        cmd_synthesize,
        cmd_master,
        cmd_produce,
        cmd_auto,
    )
except ImportError:
    cmd_extract = cmd_translate = cmd_script = cmd_synthesize = cmd_master = cmd_produce = cmd_auto = None

try:
    from audiobook_factory.cli.commands.audio import (
        cmd_soundscape,
        cmd_bgm,
        cmd_stems,
        cmd_package,
        cmd_direct,
        cmd_render,
        cmd_timeline,
    )
except ImportError:
    cmd_soundscape = cmd_bgm = cmd_stems = cmd_package = cmd_direct = cmd_render = cmd_timeline = None

try:
    from audiobook_factory.cli.commands.audit import (
        cmd_audit_book,
        cmd_audit,
        cmd_doctor,
    )
except ImportError:
    cmd_audit_book = cmd_audit = cmd_doctor = None

try:
    from audiobook_factory.cli.commands.bank import (
        cmd_bank,
    )
except ImportError:
    cmd_bank = None

try:
    from audiobook_factory.cli.commands.keys import (
        cmd_keys,
    )
except ImportError:
    cmd_keys = None

__all__ = [
    "cmd_extract",
    "cmd_translate",
    "cmd_script",
    "cmd_synthesize",
    "cmd_master",
    "cmd_produce",
    "cmd_auto",
    "cmd_soundscape",
    "cmd_bgm",
    "cmd_stems",
    "cmd_package",
    "cmd_direct",
    "cmd_render",
    "cmd_timeline",
    "cmd_audit_book",
    "cmd_audit",
    "cmd_doctor",
    "cmd_bank",
    "cmd_keys",
]
