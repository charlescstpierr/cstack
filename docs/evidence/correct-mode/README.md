# Refus d’activation : corpus historique bilingue

Six findings dans quatre PR : #70, #90, #91, #92. Le catalogue de #114 et l’API ont les mêmes 199 IDs. `history.json` garde les commentaires et les commits revus ; son historique de chemin complète le relevé. Aucun commit explicitement nommé revert n’a été trouvé dans les refs disponibles. Les PR #92 et #114 sont encore ouvertes ; cette branche part de main, sans reprendre leurs autres modifications.

Niveau choisi : tests de comportement, avec un corpus de 33 cas français et anglais. L’architecture ne peut supprimer l’analyse des refus sans changer le comportement autorisé : le jeton canonique suivi de « do not activate this skill » doit rester inactif. Les types ne peuvent pas représenter une intention absente des données du hook. Un lint syntaxique ne peut pas classer la prose. Le corpus couvre les erreurs connues ; il ne prétend pas interpréter toute phrase possible.

Le hook extrait d’abord le texte d’instruction hors citations, code et blocs Markdown. Un refus doit ensuite viser cstack ou un pronom explicite. La grammaire française accepte les formes finies et les infinitifs. L’arrêt conserve sa commande exacte ; les négations ne l’exécutent pas. Les tests vérifient la sortie du vrai hook, son marqueur sur disque, le tour suivant et SessionStart/resume.

Chaque sortie `<comment_id>-red.log` rejoue uniquement les cas du finding correspondant sur sa révision historique. `red-main.log` prouve aussi l’échec de main avant ce changement. `green.log` est le même corpus sur le nouveau hook.

Exemple reproductible, pour les infinitifs français de #91 :

```sh
mkdir -p .cstack/correct
git fetch origin e41552f324fdf0b0f2521a85c7ade177827d03f2
git show e41552f324fdf0b0f2521a85c7ade177827d03f2:plugins/cstack/hooks/mode.py > .cstack/correct/old-mode.py
CSTACK_MODE_HOOK="$PWD/.cstack/correct/old-mode.py" CSTACK_MODE_FINDING=4211983060 python3 -m unittest discover -s tests -p test_mode_corpus.py
```

Pour rejouer les autres :

| Finding | PR | Révision revue |
|---|---|---|
| 4113802959 | #70 | `f013dba91872db1fb37edd02c472fc153e97bae0` |
| 4208736383 | #90 | `84c02ea31c2e5bc80e5476321b5ed2acd7b660de` |
| 4210984706 | #91 | `f16ad37e081e615c932be24702faf4d38b77f06b` |
| 4211983060 | #91 | `e41552f324fdf0b0f2521a85c7ade177827d03f2` |
| 4212451947 | #92 | `98427161bbb182aacafece037fed610291eaf3a6` |
| 4212756301 | #92 | `686b721ce0819eaf6592ea239fd5dd9e992ff692` |

Contrôle courant, exécuté aussi par la découverte Python de `bash scripts/check.sh` :

```sh
python3 -m unittest discover -s tests -p test_mode_corpus.py
bash scripts/check.sh
```

La sortie complète de validation est dans `check.log`. Les logs ont seulement leurs espaces finaux retirés pour `git diff --check`. Aucun modèle, aucun Codex/Claude réel, aucune revue indépendante ni interprétation sémantique d’autres formulations n’a été vérifié. Le hook est testé en sous-processus avec un répertoire de données isolé.
