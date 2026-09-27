#!/usr/bin/env python3
"""Rappel du mode cstack, l'équivalent du `reminder:` de pstack dans Cursor.

Codex lance ce hook à chaque message (`UserPromptSubmit`) et après un résumé ou une reprise
(`SessionStart`). Il ne parle que dans une conversation où l'utilisateur a invoqué `$cstack:cstack` :
ailleurs, il n'écrit rien. Il ne lit jamais le transcript et ne garde que des identifiants de session
sous `PLUGIN_DATA`. Toute erreur donne une sortie vide : le hook ne bloque jamais un message.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys

ACTIVATE = re.compile(r"\$cstack:cstack\b")
# « arrête cstack », « stop cstack », « désactive cstack », « quitte le mode cstack »…
STOP = re.compile(r"\b(?:arr[êe]te|stop|stoppe|d[ée]sactive|quitte|sors?)\b[^.\n]{0,20}\bcstack\b", re.IGNORECASE)

REMINDER = (
    "Mode cstack actif dans cette conversation. Nouvelle tâche ou tâche en cours : applique `$cstack:cstack` "
    "et, si le contexte a été résumé, relis son SKILL.md et `references/runtime/base.md` avant de continuer. "
    "Tour anodin ou arrêt demandé par l'utilisateur : n'applique pas."
)
RESUMED = " Relis aussi le point de reprise de la tâche sous `.cstack/` s'il existe."


def _marker(data_dir: Path, session_id: str) -> Path:
    # L'identifiant est haché : aucun chemin ne dépend d'une valeur externe.
    return data_dir / "sessions" / hashlib.sha256(session_id.encode()).hexdigest()


def reminder(event: dict, data_dir: Path) -> str:
    session_id = event.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return ""
    marker = _marker(data_dir, session_id)
    if event.get("hook_event_name") == "UserPromptSubmit":
        prompt = event.get("prompt") if isinstance(event.get("prompt"), str) else ""
        if STOP.search(prompt):
            marker.unlink(missing_ok=True)
            return ""
        if ACTIVATE.search(prompt):
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.touch()
        return REMINDER if marker.exists() else ""
    if event.get("hook_event_name") == "SessionStart" and marker.exists():
        return REMINDER + RESUMED
    return ""


def main() -> int:
    try:
        data = os.environ.get("PLUGIN_DATA") or os.environ.get("CLAUDE_PLUGIN_DATA")
        if not data:
            return 0
        event = json.loads(sys.stdin.read() or "{}")
        text = reminder(event, Path(data)) if isinstance(event, dict) else ""
        if text:
            sys.stdout.write(text + "\n")
    except Exception:
        # Un rappel manquant vaut mieux qu'un message bloqué.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
