# Rechercher des notes

La recherche permet à un utilisateur de trouver des notes par titre ou texte de corps, d'inspecter une note correspondante et de distinguer l'absence de résultats d'une recherche indisponible.

## Sous-fonctionnalités

- `search-open` ouvre la recherche depuis chaque point d'entrée navigateur pris en charge.
- `search-match` renvoie des correspondances dans le titre et le corps sans changer les données de note.
- `search-open-result` ouvre un résultat dans l'éditeur de note.
- `search-empty` montre un état vide complet pour une requête sans correspondance.
- `search-clear` retire la requête et restaure la vue des notes récentes.
- `search-cli` renvoie les mêmes notes correspondantes depuis le terminal.

## Comment y accéder (point de vue utilisateur)

- Choisir le bouton `Search` dans la barre d'outils du navigateur.
- Appuyer sur `/` dans le navigateur quand le focus est hors d'un champ editable.
- Exécuter `notes search <query>` dans un terminal.

## Pilotage avec control-notes

Préconditions :

- Notes est sain sur `http://127.0.0.1:4173`.
- Le répertoire de données jetable contient `Quarterly plan` avec le texte de corps `Draft budget`.
- `control-notes doctor` signale l'URL et le répertoire de données attendus.

- **Entrée barre d'outils.** Choisir le bouton `Search`. Exécuter `control-notes browser click --role button --name "Search"`. Une boîte de dialogue nommée `Search notes` apparaît avec le focus dans sa searchbox.
- **Entrée clavier.** Fermer la boîte de dialogue, donner le focus à la page et appuyer sur `/`. Exécuter `control-notes browser press --key "/"`. La même boîte de dialogue apparaît et la page n'insère pas de barre oblique.
- **Correspondance de titre.** Taper `quarterly`. Exécuter `control-notes browser fill --role searchbox --name "Search notes" --value "quarterly"`. La liste `Search results` contient `Quarterly plan` et ne contient pas `Grocery list`.
- **Correspondance de corps.** Remplacer la requête par `budget`. Exécuter `control-notes browser fill --role searchbox --name "Search notes" --value "budget"`. Le résultat `Quarterly plan` reste visible avec un extrait de correspondance de corps.
- **Ouvrir le résultat.** Choisir `Quarterly plan`. Exécuter `control-notes browser click --role link --name "Quarterly plan"`. La boîte de dialogue se ferme et le titre de l'éditeur affiche `Quarterly plan`.
- **État vide.** Rouvrir la recherche et entrer `volcano`. Exécuter `control-notes browser fill --role searchbox --name "Search notes" --value "volcano"`. Un statut nommé `No matching notes` apparaît après la fin de la recherche.
- **Effacer la requête.** Choisir `Clear search`. Exécuter `control-notes browser click --role button --name "Clear search"`. La searchbox est vide et la région `Recent notes` remplace la liste de résultats.
- **Correspondance CLI.** Rechercher depuis le terminal. Exécuter `control-notes cli -- notes search "quarterly" --format json`. Le code de sortie `0` et stdout contiennent un objet dont le titre est `Quarterly plan`.
- **Absence CLI.** Rechercher une valeur absenté. Exécuter `control-notes cli -- notes search "volcano" --format json`. Le code de sortie `0` et stdout vaut `[]`.
- **Preuve.** Capturer l'état de résultat peuplé. Exécuter `control-notes browser snapshot --aria --path artifacts/search/results.aria.txt` et `control-notes browser screenshot --path artifacts/search/results.png`. Les deux artefacts identifient Notes, la requête et `Quarterly plan`.

## Pièges

- Appuyer sur `/` pendant que l'éditeur ou la searchbox à le focus insère du texte au lieu d'ouvrir la recherche.
- Les résultats se mettent à jour après un court debounce. Attendre la liste de résultats où le statut vide, pas un sleep fixe.
- Les notes archivees sont exclues sauf si l'utilisateur active `Include archived`.
- La CLI sort par défaut un format lisible par l'humain. Utiliser `--format json` pour des assertions stables.
- Ouvrir un résultat change l'état du navigateur. Rouvrir la recherche avant de prouver une autre requête.
