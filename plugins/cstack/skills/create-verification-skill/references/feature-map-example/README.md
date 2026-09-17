# Carte de vérification Notes

Ce répertoire est la source maintenue pour vérifier le comportement de Notes visible par l'utilisateur. Lis l'index avant de piloter l'app, puis utilise le fichier de fonctionnalité correspondant comme recette.

## Préconditions de base

- Lance Notes sur `http://127.0.0.1:4173` avec un répertoire de données jetable.
- Definis `NOTES_DATA_DIR=/tmp/notes-verify-$RUN_ID` pour que les exécutions concurrentes ne partagent pas d'état.
- Seed des notes intitulées `Quarterly plan` et `Grocery list`.
- Place `control-notes` et la CLI `notes` dans `PATH`.
- Exécute `control-notes doctor` et exige l'URL, le répertoire de données et la révision de build attendus.
- Ne pilote jamais une instance qui n'a pas été démarree par cette exécution de vérification.

## Conventions de pilotage

- Démarre chaque recette depuis l'état de base sauf indication contraire de ses préconditions.
- Préfère les rôles ARIA et noms accessibles aux sélecteurs CSS ou à la position DOM.
- Traite chaque commande comme littérale. Garde les noms entre guillémets et les flags inchanges.
- Exécute les actions navigateur via `control-notes browser`.
- Exécute les actions terminal via `control-notes cli -- <command>`.
- Restaure les données seed après une mutation. Ne retire pas les artefacts de preuve pendant le nettoyage.

## Preuves et signalement des sauts

- Capture l'action utilisateur et l'état résultant, pas seulement l'écran final.
- Une preuve UI inclut un snapshot ARIA et une capture d'écran avec l'identité de l'app visible.
- Une preuve CLI inclut la commande, stdout, stderr et le code de sortie.
- Une preuve de mutation inclut une seconde vue en lecture seule de la valeur stockée.
- Enregistre l'ID de fonctionnalité et le point d'entrée utilisés avec chaque artefact.
- Signale un chemin inaccessible avec la commande tentée et la precondition non satisfaite.
- Ne signale pas un point d'entrée saute comme vérifie par un autre chemin.

## Contrat d'entrée de fonctionnalité

Chaque fichier de fonctionnalité commence par un titre H1 et un paragraphe décrivant le comportement visible par l'utilisateur. Il utilise ensuite exactement quatre sections H2 dans cet ordre.

1. `Sous-fonctionnalités` liste des ID courts avec une ligne pour chaque comportement.
2. `Comment y accéder (point de vue utilisateur)` liste chaque point d'entrée utilisateur.
3. `Pilotage avec <harness>` commence par `Préconditions :` et utilise des puces étiquetées qui associent chaque action utilisateur à une commande exacte et à un résultat observable.
4. `Pièges` liste les pièges qui peuvent gaspiller ou invalider une exécution de vérification.

Garde les détails d'implémentation hors de la carte. Nomme seulement les chemins utilisateur, poignées stables, états requis, commandes et preuves observables.

## Fonctionnalites

- [Créer une note](./create-note.md) couvre la création navigateur et CLI, l'annulation, la persistance et le nettoyage.
- [Rechercher des notes](./search.md) couvre la recherche par barre d'outils, clavier et CLI avec états de correspondance, vide et efface.
