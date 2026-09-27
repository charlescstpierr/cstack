#!/usr/bin/env python3
"""Rappel du mode cstack, l'équivalent du `reminder:` de pstack dans Cursor.

Codex lance ce hook à chaque message (`UserPromptSubmit`) et après un résumé ou une reprise
(`SessionStart`). Il ne parle que dans une conversation où l'utilisateur a invoqué `$cstack:cstack` :
ailleurs, il n'écrit rien. Il ne lit jamais le transcript et ne garde que des identifiants de session
hachés sous `PLUGIN_DATA`. Toute erreur donne une sortie vide : le hook ne bloque jamais un message.
"""

import os
import sys

ACTIVATE = "$cstack:cstack"
STOP_VERBS = ("arrête", "arrete", "stop", "stoppe", "désactive", "desactive", "quitte")
# « n'arrête pas cstack », « don't stop cstack » : une négation juste avant le verbe garde le mode.
NEGATIONS = ("n", "ne", "t", "not", "never", "jamais")
# Un pointeur vers les règles, pas une copie : `references/runtime/base.md` reste la source.
REMINDER = "Mode cstack actif : tâche nouvelle ou en cours → applique `$cstack:cstack` ; tour anodin ou arrêt demandé → non."
AFTER_SUMMARY = "Mode cstack actif et contexte résumé : relis `references/runtime/base.md` de `$cstack:cstack` avant de continuer."


def _stop_requested(prompt: str) -> bool:
    # « arrête cstack », « stop cstack »… : le verbe juste avant « cstack », pas une négation plus loin.
    # Apostrophes droite et courbes (claviers macOS et iOS) séparent aussi les mots.
    words = prompt.lower().translate(str.maketrans({ch: " " for ch in ",.;:!?«»\"'’‘"})).split()
    return any(word == "cstack" and index and words[index - 1] in STOP_VERBS
               and (index < 2 or words[index - 2] not in NEGATIONS) for index, word in enumerate(words))


def reminder(raw: str, data: str) -> str:
    sessions = os.path.join(data, "sessions")
    # Chemin chaud : hors cstack, sortir avant tout import ou accès disque coûteux.
    if ACTIVATE not in raw and not os.path.isdir(sessions):
        return ""
    import hashlib
    import json

    event = json.loads(raw)
    session_id = event.get("session_id")
    if not session_id:
        return ""
    # L'identifiant est haché : aucun chemin ne dépend d'une valeur externe.
    marker = os.path.join(sessions, hashlib.sha256(session_id.encode()).hexdigest())
    if event.get("hook_event_name") == "SessionStart":
        return AFTER_SUMMARY if os.path.exists(marker) else ""
    prompt = event.get("prompt") or ""
    if _stop_requested(prompt):
        if os.path.exists(marker):
            os.remove(marker)
        return ""
    if ACTIVATE in prompt:
        os.makedirs(sessions, exist_ok=True)
        open(marker, "a").close()
    return REMINDER if os.path.exists(marker) else ""


def main() -> int:
    data = os.environ.get("PLUGIN_DATA")
    try:
        text = reminder(sys.stdin.read(), data) if data else ""
        if text:
            sys.stdout.write(text + "\n")
    except Exception:
        pass  # Un rappel manquant vaut mieux qu'un message bloqué.
    return 0


if __name__ == "__main__":
    sys.exit(main())
