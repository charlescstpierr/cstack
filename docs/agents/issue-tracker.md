# Issue tracker: GitHub

Les tickets et spécifications vivent dans les GitHub Issues de
`charlescstpierr/cstack`.

Utiliser `gh-axi` lorsqu'il est disponible, sinon `gh`.
Les commandes ci-dessous utilisent la syntaxe de référence de `gh`.

## Opérations

- Créer : `gh issue create --title "..." --body-file <fichier>`
- Lire : `gh issue view <numéro> --comments`
- Lister : `gh issue list --state open`
- Commenter : `gh issue comment <numéro> --body-file <fichier>`
- Ajouter un label : `gh issue edit <numéro> --add-label "..."`
- Retirer un label : `gh issue edit <numéro> --remove-label "..."`
- Fermer : `gh issue close <numéro>`

Exécuter depuis ce dépôt ou préciser `--repo charlescstpierr/cstack`.
Utiliser un fichier pour préserver les corps multilignes.

« Publier dans le tracker » signifie créer une GitHub Issue.
« Consulter le ticket » signifie lire l'issue et ses commentaires.
Toute opération reste soumise au périmètre autorisé par l'utilisateur.

## Pull requests as a triage surface

PRs as a request surface: no.
