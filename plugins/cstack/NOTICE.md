# Provenance

cstack est une adaptation indépendante, pour Codex, du projet pstack de Lauren Tan.

- Source : https://github.com/cursor/plugins/tree/889ec4b68fa5aab0e867dad71ec3fdf386ae48f3/pstack
- Commit amont : `889ec4b68fa5aab0e867dad71ec3fdf386ae48f3`
- Version du manifeste amont : `0.15.2`
- Copyright original : Copyright (c) 2026 Lauren Tan
- Licence : MIT. La licence originale est préservée dans LICENSE.
- Version du plugin cstack : `0.4.0`
- Catalogue : 29 compétences, 23 références de principes, 23 guides d'exécution, deux invites d'agents

L'adaptation remplace les instructions d'exécution, le routage de modèles et le paquetage de plugin propres à Cursor par des processus natifs Codex. Les fichiers modifiés conservent la licence originale. cstack n'est pas un produit officiel de Cursor ou d'OpenAI.

L’instantané source est enregistré dans le `UPSTREAM.json` du dépôt. La [documentation de portage](https://github.com/charlescstpierr/cstack/blob/main/docs/PORTING.md) comptabilise les compétences, guides d'exécution, invites d'agents et intégrations non prises en charge. Les liens d'attribution source sont conservés volontairement ; ce ne sont pas des dépendances d'exécution.

`deslop` est original à cstack. Ce n'est pas un portage. pstack livrait `/deslop` dans le plugin séparé `cursor-team-kit` et n'avait pas de source portable.

## Adaptations de Matt Pocock

Les préparations optionnelles de clarification, documentation de domaine, Horizon, audit d'architecture, configuration de projet et certaines méthodes de revue/rédaction adaptent les compétences de Matt Pocock, version 1.2.3, commit `3cca18b368ae95cdbdebbff572ccafa662551015`. Copyright (c) 2026 Matt Pocock. Le texte MIT est préservé dans [LICENSE-MATT-POCOCK](LICENSE-MATT-POCOCK) ; [l'inventaire d'adaptation](sources/matt-pocock.json) enregistre les chemins source et les empreintes.

Le portage natif cstack change les noms d'invocation, les appels d'outils et les chemins d'état local. Horizon conserve les limites de planification des décisions et d'entrée humaine. La configuration de projet utilise des blocs de document gérés et les rôles de modèles Codex existants. Les axes de revue réutilisent le comité cstack sélectionné au lieu d'ajouter un autre comité. Aucun plugin ni configuration Matt n'est requis à l'exécution.

[Source originale épinglée](https://github.com/mattpocock/skills/tree/3cca18b368ae95cdbdebbff572ccafa662551015).
