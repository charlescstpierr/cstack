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
AUTO_RESUME = " Si une tâche cstack était en cours avant ce résumé, relis aussi son point de reprise sous `.cstack/`."


def _auto_start_marker() -> str:
    base = os.environ.get("XDG_CONFIG_HOME", "")
    if not os.path.isabs(base):
        base = os.path.join(os.path.expanduser("~"), ".config")
    # Un dossier relatif changerait de réglage avec le dossier courant : sans chemin absolu, pas de réglage.
    return os.path.join(base, "cstack", "auto-start") if os.path.isabs(base) else ""


def _auto_start() -> bool:
    path = _auto_start_marker()
    return bool(path) and os.path.isfile(path)


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
    # Le réglage n'est lu que pour un début de session ou un message qui nomme cstack.
    auto = ("SessionStart" in raw or "cstack" in raw) and _auto_start()
    if (not auto and ACTIVATE not in raw and CLAUDE_ACTIVATE not in raw and "[$cstack]" not in raw
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
    # « arrête cstack » doit tenir jusqu'à la fin de la conversation, résumés compris.
    stopped = marker + ".off"
    if event.get("hook_event_name") == "SessionStart":
        resumed = event.get("source") not in ("startup", "clear")
        if resumed and os.path.exists(marker):
            return AFTER_SUMMARY
        skill = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills", "cstack", "SKILL.md")
        # Le chemin entre dans le contexte du modèle : un nom de dossier ne doit pas y écrire de consigne.
        if not auto or os.path.exists(stopped) or any(character in skill for character in "`\r\n"):
            return ""
        return AUTO_START.format(skill=skill) + (AUTO_RESUME if resumed else "")
    prompt = event.get("prompt") or ""
    if _stop_requested(prompt):
        try:
            os.remove(marker)
        except FileNotFoundError:
            pass
        if auto:
            os.makedirs(sessions, exist_ok=True)
            open(stopped, "a").close()
        return ""
    if _activation_requested(prompt):
        os.makedirs(sessions, exist_ok=True)
        open(marker, "a").close()
        try:
            os.remove(stopped)
        except FileNotFoundError:
            pass
    return REMINDER if os.path.exists(marker) else ""


def _switch(arguments: list) -> int:
    if arguments not in (["auto", "on"], ["auto", "off"], ["auto", "status"]):
        sys.stderr.write("utilisation: mode.py auto on|off|status\n")
        return 2
    path = _auto_start_marker()
    try:
        if not path:
            raise OSError("aucun dossier de configuration absolu")
        if arguments[1] == "on":
            if os.path.islink(path):
                raise OSError("le réglage est un lien symbolique")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "a").close()
        elif arguments[1] == "off" and os.path.lexists(path):
            os.remove(path)
    except OSError as error:
        sys.stderr.write(f"démarrage automatique de cstack : réglage inchangé ({error})\n")
        return 1
    sys.stdout.write(f"démarrage automatique de cstack : {'activé' if _auto_start() else 'éteint'} ({path})\n")
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
