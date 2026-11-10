# Provenance : un seul format et un seul calcul

Le catalogue de #114 compte quinze findings dans six PR. Douze se trouvent dans #90–#92, dont onze dans #91 et #92. Les 199 IDs du catalogue correspondent exactement à ceux de l’API ; `history.json` conserve les commentaires, leurs révisions et l’historique Git des deux consommateurs. Aucun commit explicitement nommé revert n’a été trouvé dans les refs disponibles. La PR #116 travaille aussi sur ces consommateurs ; cette branche indépendante part de main, sans intégrer ses autres modifications.

Niveau choisi : architecture, le plus haut de `/correct`. `scripts/provenance.py` est la seule source du format, des exclusions, du calcul d’arbre et de la configuration canonique d’un cas. Les wrappers publics gardent leurs contrats de retour et d’erreur. Un objet tree de Git seul ne représente pas les dossiers vides, toutes les permissions, les fichiers non suivis ni l’index courant. Le module combine un manifeste du système de fichiers avec les commandes de plomberie Git, plutôt que de reproduire le stockage interne de Git.

Le format v3 authentifie les fichiers, permissions, dossiers et liens de fichiers internes, ainsi que HEAD, refs, index et configuration Git locale à la racine. Les liens de dossiers, liens de fichiers extérieurs, fichiers spéciaux, dépôts imbriqués et opérations Git en cours sont refusés. Les branches sans commit sont représentées par un OID nul. Les copies répétées conservent les liens internes et leur sémantique. Les formats v1/v2 exigent une régénération des attentes.

La matrice teste les consommateurs publics du générateur et du runner contre les mêmes mutations. Dix contrôles nouveaux échouent chacun sur la révision historique de leur finding ; les contrôles déjà présents sur la validation des attentes et la configuration des cas sont conservés. `red-main.log` montre les lacunes avant le changement. Une FIFO créée pendant un tour simulé ne supprime plus son résultat : le reçu conserve le tour terminé et le flux brut, marque le hachage absent et rend les verdicts `unverified`.

Reproduction, pour l’oubli des dossiers dans #91 :

```sh
mkdir -p .cstack/correct/old-provenance
git fetch origin e41552f324fdf0b0f2521a85c7ade177827d03f2
git show e41552f324fdf0b0f2521a85c7ade177827d03f2:scripts/behavior-scenarios.py > .cstack/correct/old-provenance/behavior-scenarios.py
git show e41552f324fdf0b0f2521a85c7ade177827d03f2:scripts/verify-behavior.py > .cstack/correct/old-provenance/verify-behavior.py
CSTACK_PROVENANCE_SCRIPTS="$PWD/.cstack/correct/old-provenance" python3 -m unittest discover -s tests -p test_provenance.py -k 4211983053
```

Autres contrôles historiques, même commande avec le numéro après `-k` et les fichiers de la révision indiquée :

| Finding | PR | Révision |
|---|---|---|
| 4210984697 | #91 | `f16ad37e081e615c932be24702faf4d38b77f06b` |
| 4211195095 | #91 | `92494de2d749a3f5c2d061c1fd368c1cd331e43a` |
| 4211485693 | #91 | `2255dfc2f586aab45f82fa7adb8fc27f00547530` |
| 4211983045 | #91 | `e41552f324fdf0b0f2521a85c7ade177827d03f2` |
| 4211983053 | #91 | `e41552f324fdf0b0f2521a85c7ade177827d03f2` |
| 4212089947 | #91 | `e41552f324fdf0b0f2521a85c7ade177827d03f2` |
| 4212089956 | #91 | `e41552f324fdf0b0f2521a85c7ade177827d03f2` |
| 4212451943 | #92 | `98427161bbb182aacafece037fed610291eaf3a6` |
| 4212451953 | #92 | `98427161bbb182aacafece037fed610291eaf3a6` |
| 4212756294 | #92 | `686b721ce0819eaf6592ea239fd5dd9e992ff692` |

Contrôle courant, exécuté aussi par `bash scripts/check.sh` :

```sh
python3 -m unittest discover -s tests -p test_provenance.py
bash scripts/check.sh
```

Sorties rouges, `green.log` et validation complète `check.log` sont conservées. Les logs ont seulement leurs espaces finaux retirés. Aucun modèle ni serveur Codex réel n’est lancé ; le test du reçu simule le transport et crée une vraie FIFO. Pas de revue indépendante ni exécution macOS/Python 3.9 de ces nouveaux contrôles. Le périmètre exclut toujours `node_modules` et `__pycache__`, ainsi que le stockage interne des objets/reflogs et la configuration Git globale. Les empreintes Git décrivent les racines contenant `.git` ; elles ne constituent pas une attestation de l’environnement extérieur.
