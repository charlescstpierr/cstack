#!/usr/bin/env python3
"""Rappel du mode cstack, l'équivalent du `reminder:` de pstack dans Cursor.

Codex lance ce hook à chaque message (`UserPromptSubmit`) et au début d'une session, après un résumé
ou une reprise (`SessionStart`). Il ne parle que dans une conversation où l'utilisateur a invoqué
`$cstack:cstack`, ou au début d'une session quand l'utilisateur a activé le démarrage automatique sur
la machine (`mode.py auto on`). Ailleurs, il n'écrit rien. Il ne lit jamais le transcript et ne garde
que des identifiants de session hachés sous `PLUGIN_DATA`. Toute erreur donne une sortie vide : le hook
ne bloque jamais un message.
"""

import os
import sys

ACTIVATE = "$cstack:cstack"
# Claude Code invoque la même compétence par sa commande slash.
CLAUDE_ACTIVATE = "/cstack:cstack"
# Comme l'activation, l'arrêt est une commande exacte (« arrête cstack ») ; une phrase plus longue
# reste au jugement du modèle, que le rappel invite déjà à ne pas appliquer cstack sur demande d'arrêt.
STOP_VERBS = ("arrête", "arrete", "stop", "stoppe", "désactive", "desactive", "quitte")
# Un pointeur vers les règles, pas une copie : `references/runtime/base.md` reste la source.
REMINDER = "Mode cstack actif : tâche nouvelle ou en cours → applique `$cstack:cstack` ; tour anodin ou arrêt demandé → non."
AFTER_SUMMARY = (
    "Mode cstack actif et contexte résumé : relis `references/runtime/base.md` de `$cstack:cstack` "
    "et le point de reprise de la tâche active dont le résumé nomme le chemin sous `.cstack/` "
    "(voir `references/runtime/etat.md`) avant de continuer."
)


# Réglage de la machine, éteint par défaut : seul `mode.py auto on`, lancé à la demande de l'utilisateur, l'active.
AUTO_START = (
    "Démarrage automatique de cstack : l'utilisateur l'a activé sur cette machine, ce qui vaut invocation "
    "explicite de `$cstack:cstack`. Quand la tâche touche plus d'un fichier ou une signature appelée ailleurs, "
    "demande un choix de conception, ou porte sur un bug de cause inconnue ou une lenteur, ouvre en entier "
    "`{skill}` et suis-le. Pour une question, une édition d'une ligne ou un changement contenu dans un fichier "
    "avec un test évident, travaille directement, sans cstack. Les instructions de l'utilisateur et du projet "
    "priment, et « arrête cstack » l'éteint pour cette conversation."
)


def _auto_start_marker() -> str:
    base = os.environ.get("XDG_CONFIG_HOME", "")
    if not os.path.isabs(base):
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "cstack", "auto-start")


def _stop_requested(prompt: str) -> bool:
    words = prompt.lower().strip(" \t\n.!?…").split()
    return len(words) == 2 and words[0] in STOP_VERBS and words[1] == "cstack"


def _activation_requested(prompt: str) -> bool:
    import re

    # Le hook n'a pas le signal structuré du sélecteur : n'accepter que les formes
    # de commande explicites, jamais une mention citée ou insérée dans une explication.
    invocation = re.match(
        r"\s*(?:(?i:utilise|applique|active|use|invoke|activate)\s+)?"
        r"(?:\$cstack:cstack|/cstack:cstack|\[\$cstack(?::cstack)?\]\((?P<path>[^)\r\n]+)\))(?=\s|$)",
        prompt,
    )
    if not invocation:
        return False
    path = invocation.group("path")
    if path and not path.strip("<>").endswith("/skills/cstack/SKILL.md"):
        return False
    # Un refus qui cible cstack reste prioritaire, même plus loin dans le message.
    refusal = re.search(
        r"\b(?:ne\s+l['’](?:activ|utilis|appliqu)\w*\s+pas\b"
        r"|(?:ne\s+|n['’])activ\w*\s+pas\s+(?:cstack|\$cstack:cstack)\b"
        r"|(?:do\s+not|don['’]t)\s+(?:activate|use|invoke)\s+"
        r"(?:it|cstack|\$cstack:cstack|(?:this|the)\s+(?:cstack\s+)?skill)\b)",
        prompt[invocation.end():],
        re.IGNORECASE,
    )
    return refusal is None


def reminder(raw: str, data: str) -> str:
    sessions = os.path.join(data, "sessions")
    # Chemin chaud : hors cstack, sortir avant tout import ou accès disque coûteux.
    starting = "SessionStart" in raw and os.path.exists(_auto_start_marker())
    if (not starting and ACTIVATE not in raw and CLAUDE_ACTIVATE not in raw and "[$cstack]" not in raw
            and not os.path.isdir(sessions)):
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
        if event.get("source") not in ("startup", "clear") and os.path.exists(marker):
            return AFTER_SUMMARY
        if not os.path.exists(_auto_start_marker()):
            return ""
        plugin = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return AUTO_START.format(skill=os.path.join(plugin, "skills", "cstack", "SKILL.md"))
    prompt = event.get("prompt") or ""
    if _stop_requested(prompt):
        try:
            os.remove(marker)
        except FileNotFoundError:
            pass
        return ""
    if _activation_requested(prompt):
        os.makedirs(sessions, exist_ok=True)
        open(marker, "a").close()
    return REMINDER if os.path.exists(marker) else ""


def _switch(arguments: list) -> int:
    path = _auto_start_marker()
    if arguments == ["auto", "on"]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "a").close()
    elif arguments == ["auto", "off"]:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    elif arguments != ["auto", "status"]:
        sys.stderr.write("utilisation: mode.py auto on|off|status\n")
        return 2
    state = "activé" if os.path.exists(path) else "éteint"
    sys.stdout.write(f"démarrage automatique de cstack : {state} ({path})\n")
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        return _switch(sys.argv[1:])
    data = os.environ.get("PLUGIN_DATA") or os.environ.get("CLAUDE_PLUGIN_DATA")
    try:
        text = reminder(sys.stdin.read(), data) if data else ""
        if text:
            sys.stdout.write(text + "\n")
    except Exception:
        pass  # Un rappel manquant vaut mieux qu'un message bloqué.
    return 0


if __name__ == "__main__":
    sys.exit(main())
