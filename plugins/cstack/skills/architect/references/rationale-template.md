# Modèle de justification

La prose qui accompagne l'ébauche de types. Une page. Titres en casse phrase, pas de boilerplate. Remplace les notes en italique par du contenu réel.

## Problème

*Un paragraphe. Ce que nous essayons de faire, et ce qui dans le système existant ou les contraintes rend la forme non évidente. Si la [Phase A](../SKILL.md#phase-a-ancrer-le-problème) a fait émerger des contraintes que la conception doit respecter (types existants avec lesquels interopérer, appelants à ne pas casser, invariants qui traversaient notre frontière), nomme-les ici pour que le lecteur voie les mêmes contraintes que toi.*

## Usage (vue de l'appelant)

*Écris ceci d'abord, avant l'ébauche de types. Montre le README ou démarrage rapide lu par le consommateur, plus deux ou trois sites d'appel réalistes dans son propre code. Ce qu'il importe, ce qu'il appelle, ce qui revient. L'ébauche de types dans [Forme](#forme) en dérive. Les deux doivent correspondre. Quand ils divergent, réconcilie l'ébauche avec l'usage, pas l'inverse. L'expérience de l'appelant est la spec. Les types la servent.*

## Forme

*L'architecture recommandée. Structures de données d'abord. Puis comment les données circulent à travers les signatures. Nomme les décisions porteuses. Indique quels invariants sont encodés dans les types, où vit la validation et ce que le système choisit délibérément de ne pas faire. Juge explicitement la profondeur d'interface. Indique quelle complexité la surface publique cache, ce qui reste exposé aux appelants et pourquoi l'interface n'est pas plus grande que nécessaire. Cite le principe derrière chaque décision (p. ex. `selon boundary-discipline`). Ne le répète pas.*

## Décision de synthèse

*Remplie par [arena](../../arena/SKILL.md). Note quel candidat est devenu la base et pourquoi, ce qui a été adapté depuis chacun des autres, et ce qui a été rejeté et pourquoi.*

## Compromis acceptés

*Une puce par compromis fait par la forme choisie. Forme : "nous acceptons X en échange de Y." Nomme tout ce qu'un futur lecteur pourrait prendre pour un oubli, y compris les choses qui ressemblent à de l'optimisation prématurée ou de la simplification prématurée.*

## Alternatives considérées

*Obligatoire. Nomme au moins une forme alternative concrète, avec une ligne expliquant pourquoi elle a perdu. Juge chaque alternative selon la profondeur d'interface, pas seulement la simplicité d'implémentation. Nomme la complexité qu'elle expose aux appelants et celle qu'elle cache. Deux ou trois alternatives vont ici quand l'espace de conception avait de vrais concurrents. Une seule suffit quand les contraintes forçaient la réponse, avec la conclusion formulée comme "c'était la seule forme viable parce que...". Évite de lister des variantes de la même forme. Cette section couvre les alternatives de conception examinées puis rejetées par la forme choisie, pas les autres candidats de exécuteurs.*

## Questions ouvertes et risques

*Ce que tu as remarqué pendant l'ébauche et qui nécessite l'avis de l'humain, ainsi que les risques à signaler avant l'implémentation. Formule en questions, pas en assertions, pour que la réponse humaine soit la résolution plutôt qu'un commentaire.*

## Prochaine étape d'implémentation

*La première chose à construire contre l'ébauche. Une phrase. Ce que tu commencerais à écrire immédiatement après la synthèse (ou après validation de Phase D si un checkpoint a été activé).*
