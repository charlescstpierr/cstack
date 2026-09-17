# Signaux rouges de conception

Passe chaque candidat au crible avant la synthèse. Un signal rouge est une raison de réviser ou rejeter la forme.

## Module superficiel

Un module superficiel expose une grande interface tout en cachant peu de complexité. Juge la profondeur par la capacité et la politique cachées derrière la surface publique, relativement à la taille de cette surface. Préfère une interface simple soutenue par un comportement substantiel.

Ne confonds pas module profond et chaîne d'appels profonde. Une chaîne d'appels profonde éparpille la compréhension entre les couches. Un module profond concentre la capacité derrière une interface.

Cherche ces signes :

- Les appelants coordonnent plusieurs méthodes pour terminer une opération.
- Les options publiques exposent des étapes internes ou des choix d'implémentation.
- Apprendre l'interface n'évite pas à l'appelant d'apprendre l'implémentation.

## Fuite d'information

La fuite d'information fait dépendre plusieurs modules de la même décision interne. Un détail de représentation, de politique ou de protocole apparaît à plusieurs endroits, si bien que le changer exige des modifications coordonnées.

Les réexports publics de types de transport ou wire sont des fuites. Analyse les données externes en types de domaine derrière l'interface. Garde privés les schémas de stockage, objets de framework et détails de protocole.

## Décomposition temporelle

La décomposition temporelle organise les modules par ordre d'exécution plutôt que par connaissance possédée. Des étapes séparées load, validate, transform et save répètent souvent une représentation et ses invariants à plusieurs frontières.

Regroupe le code autour de la connaissance du domaine et de la propriété. Des méthodes qui s'exécutent à des moments différents peuvent quand même appartenir à un même module lorsqu'elles protègent les mêmes décisions.

## Méthode relais

Une méthode relais transmet les mêmes arguments à une autre méthode de même forme. Elle ajoute une couche sans cacher de complexité.

Supprime-la ou déplace la responsabilité vers le module capable de terminer l'opération. Garde une frontière de forwarding seulement quand elle ajoute une politique, une adaptation ou une abstraction distincte.
