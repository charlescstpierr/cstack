# Discipline des frontières

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Placez la validation, le rétrécissement de types et la gestion des erreurs aux frontières du système. Faites confiance au code interne sans condition. La logique métier vit dans des fonctions pures. La coquille est mince et mécanique.

**Pourquoi :** la validation dispersée est bruyante, redondante et donne un faux sentiment de sécurité. Gardez la logique hors du câblage du framework afin qu'elle puisse être testée sans le framework.

**Le motif :**
- **Aux frontières** (arguments CLI, fichiers de config, API externes, protocoles réseau) : valider, retourner les erreurs, gérer défensivement.
- **Dans le système :** données typées, propagation d'erreurs, pas de revalidation. Faites confiance aux types.
- **À travers la frontière.** Exposez les concepts du domaine, pas la représentation privée de la frontière. Gardez le mécanisme général à l'intérieur et la politique spécialisée au bord.

**Applications:**

Validation et gestion des erreurs :
- Valider la config au moment du analyse (la frontière), pas dans la logique métier
- Analyseur les données brutes en types de domaine à la frontière
- Ne pas réexporter les types de transport, stockage, framework ou filaire via la surface publique
- Pas de vérifications nil redondantes au fond des chaînes d'appels si la frontière a déjà validé

Organisation du code :
- Logique métier dans des fonctions pures sans dépendances au framework
- Fonctions d'analyse : transformations pures d'octets bruts vers un état typé
- Construction d'invite : état structuré en entrée, chaîne en sortie
- Scoring et évaluation : transformations pures d'un état vers des résultats

**Les tests :**
- « Ces données traversent-elles une frontière système maintenant ? » Sinon, la validation est redondante.
- « Ceci peut-il être une fonction pure que la coquille appelle simplement ? » Si oui, extrayez-la.
