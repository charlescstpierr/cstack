---
name: make-bot-ui
description: "Utiliser pour $cstack:make-bot-ui ou quand on demande de construire l'UI webhook Cursor Grok Bot upstream. Signale la limite d'intégration dans Codex App et CLI."
---

# Make Bot UI

Contrat d’exécution : [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Cette capacité upstream dépend des routines webhook Cursor Grok Bot, du stockage des clés d'expéditeur de routine et des événements de réveil propres à Cursor. Codex App et CLI n'exposent pas d'équivalent prêt à remplacer, donc cette skill ne peut pas construire ni prétendre fournir un substitut exécutable.

Signale la limite et lie l'implémentation upstream exacte : [plugins Cursor, pstack `make-bot-ui`](https://github.com/cursor/plugins/blob/27e2a62ff94f9af4b5e68435e41cdceacadb840c/pstack/skills/make-bot-ui/SKILL.md).

Si l'utilisateur demande séparément une UI web locale normale, traite-la comme une nouvelle tâche d'application bornée. N'implique pas qu'elle réveille un Grok Bot ou préserve la sémantique webhook upstream.
