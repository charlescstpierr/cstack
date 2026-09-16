# Archéologie du code (git + dépôt)

## Ce que cette source contient

- Historique de commits (messages, dates, auteurs, diffs)
- Descriptions de PR, commentaires de revue et threads de discussion (via `gh`)
- Commentaires inline, TODOs, FIXMEs, notes de dépréciation
- ADRs (architectural decision records) si le dépôt en conserve
- Tests. Les noms et assertions encodent souvent les cas limites qui ont motivé un changement
- Fichiers liés modifiés dans les mêmes commits (signal de co-changement)
- Entrées CHANGELOG, notes de release dans le dépôt
- IDs d'issues/tickets mentionnés dans les messages de commit et corps de PR

La source la plus fiable, directement liée au code, et la plus complète. Tout ce qui est passé par le dépôt devrait être ici.

## Comment la chercher

Étends la liste de commits graine :

```bash
# Historique complet du fichier à travers les renommages
git log --follow --oneline -- <file>

# Pickaxe : commits qui ont ajouté ou retiré ce texte exact
git log -S '<exact_string_from_code>' -- <file>

# Ou pour les motifs :
git log -G '<regex>' -- <file>

# Qui a écrit chaque ligne et quand
git blame -L <start>,<end> <file>

# Le diff complet d'un commit précis
git show <hash>

# Commits entre deux points qui touchent ce fichier
git log <old>..<new> -p -- <file>
```

Pour chaque commit substantiel, récupère le contexte PR :

```bash
# Trouver le numéro de PR depuis le commit de merge ou la branche
git log -1 --format=%B <hash>

# Contexte PR complet : corps, commentaires de revue, issues liées
gh pr view <number> --json title,body,author,createdAt,mergedAt,labels,closingIssuesReferences,comments,reviews,files

# Les champs --json reviews et comments contiennent le vrai signal
```

Cherche les docs hors bande :

```bash
# Les ADR vivent souvent dans docs/adr/ ou équivalent
rg -l -i 'architecture.decision' --glob '*.md'

# TODOs et FIXMEs près de la cible
rg -n -C2 '(TODO|FIXME|HACK|XXX|NOTE)' <target_file>

# Tests liés. Les noms encodent souvent le "pourquoi"
rg -l '<symbol>' --glob '*test*'
```

## À quoi ressemble une bonne preuve ici

- Une description de PR qui explique le problème résolu, pas seulement le changement ("ceci corrige le bug de pagination qui provoquait X")
- Un long thread de revue où des alternatives ont été débattues
- Un commentaire inline près de la ligne cible qui explique une contrainte non évidente
- Un test nommé `test_handles_edge_case_when_X` qui révèle un cas limite motivant le code
- Un message de commit qui référence un ID de ticket ou incident
- Une entrée CHANGELOG qui résume la justification visible par l'utilisateur

## Pièges courants

- **Plaines de squash-merge.** Si le dépôt squash les PR, les commits individuels de la branche sont perdus. Replie-toi sur le corps de PR et les commentaires.
- **Messages de commit trompeurs.** "Petit refactor" cache parfois un changement de comportement intentionnel. Regarde le diff, pas le message.
- **Motifs cargo-cultés.** L'auteur peut avoir copié un motif sans comprendre pourquoi. Vérifie si le motif vient d'ailleurs dans le codebase et enquête sur *ce* commit.
- **Commits de bots et auto-merges.** Dependabot, Renovate et les backports automatisés portent rarement la motivation. Saute-les quand tu cherches l'intention.
- **Traiter le code comme preuve d'intention.** Le code lui-même n'est pas une preuve de pourquoi il existe. Les preuves viennent des messages de commit, PR, commentaires, tests, docs. Ne cite pas "la fonction s'appelle X" comme preuve d'intention.

## Quoi retourner

Chaque commit/PR/commentaire qui pèse sur la question, avec :
- Le texte exact (cité)
- Le hash / numéro de PR / file:line
- Auteur et date
- S'il est direct (répond explicitement à la question) ou circonstanciel
