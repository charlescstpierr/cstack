# Créer une note

Créer une note permet à un utilisateur d'enregistrer depuis le navigateur ou la CLI une note avec titre, d'annuler un brouillon inachevé et de confirmer la note enregistree depuis une seconde vue utilisateur.

## Sous-fonctionnalités

- `create-open` ouvre un éditeur vide depuis chaque point d'entrée navigateur.
- `create-save` persiste un titre et un corps.
- `create-cancel` abandonne un brouillon navigateur inachevé.
- `create-cli` crée la même forme de note depuis le terminal.

## Comment y accéder (point de vue utilisateur)

- Choisir le bouton `New note` dans la barre d'outils du navigateur.
- Appuyer sur `n` dans le navigateur quand le focus est hors d'un champ editable.
- Exécuter `notes create --title <title> --body <body>` dans un terminal.

## Pilotage avec control-notes

Préconditions :

- Notes est sain sur `http://127.0.0.1:4173`.
- Aucune note n'est intitulée `Release checklist`.
- `control-notes doctor` signale l'URL attendue et le répertoire de données jetable.

- **Ouvrir l'éditeur.** Choisir `New note`. Exécuter `control-notes browser click --role button --name "New note"`. Un formulaire nommé `Note editor` apparaît avec le focus dans la zone de texte `Title`.
- **Entrer le contenu.** Taper le titre et le corps. Exécuter `control-notes browser fill --role textbox --name "Title" --value "Release checklist"` et `control-notes browser fill --role textbox --name "Body" --value "Tag and publish"`. Le bouton `Save note` devient actif.
- **Enregistrer la note.** Choisir `Save note`. Exécuter `control-notes browser click --role button --name "Save note"`. Un statut nommé `Note saved` apparaît et le titre affiche `Release checklist`.
- **Confirmer la persistance.** Revenir à la liste des notes et rouvrir la note. Exécuter `control-notes browser click --role link --name "All notes"` et `control-notes browser click --role link --name "Release checklist"`. L'éditeur montre les deux valeurs enregistrées.
- **Annuler le brouillon.** Ouvrir une nouvelle note, entrer `Discard me`, puis choisir `Cancel`. Exécuter `control-notes browser click --role button --name "New note"`, `control-notes browser fill --role textbox --name "Title" --value "Discard me"` et `control-notes browser click --role button --name "Cancel"`. La liste des notes revient et n'a aucun lien `Discard me`.
- **Entrée CLI.** Créer une seconde note. Exécuter `control-notes cli -- notes create --title "CLI note" --body "Created from terminal" --format json`. Le code de sortie `0` et stdout contiennent l'ID et le titre de la nouvelle note.
- **Preuve.** Rouvrir les deux notes enregistrées depuis `All notes`. Exécuter `control-notes browser snapshot --aria --path artifacts/create-note/list.aria.txt` et `control-notes browser screenshot --path artifacts/create-note/list.png`. Les artefacts montrent `Release checklist` et `CLI note`.

## Pièges

- Appuyer sur `n` pendant qu'une zone de texte a le focus saisit le caractère au lieu d'ouvrir un nouvel éditeur.
- Les titres sont trimmes à l'enregistrement. Asserter le titre rendu, pas la valeur saisie dans le brouillon.
- Un statut d'enregistrement seul ne suffit pas comme preuve. Rouvrir la note depuis la liste.
- Retirer `Release checklist` et `CLI note` pendant le nettoyage des fixtures, mais conserver leurs artefacts de preuve.
