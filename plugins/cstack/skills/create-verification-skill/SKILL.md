---
name: create-verification-skill
description: "Génère une skill de vérification locale au projet qui pilote l'app comme un utilisateur le ferait, quels que soient le langage, le framework ou la plateforme. Utiliser pour $cstack:create-verification-skill, \"crée une skill de contrôle pour ce dépôt\", ou quand un projet n'a aucun moyen scriptable de prouver le comportement UI/CLI/service."
---

# Créer une skill de vérification

Runtime : [intégrations](../cstack/references/runtime/integrations.md).

Tout projet sérieux a besoin d'une façon scriptée de piloter la vraie app et de prouver le comportement : la lancer, exercer une fonctionnalité comme un utilisateur le ferait, puis capturer des preuves. Cette skill génère une skill locale au projet dans `.agents/skills/verify-<app>/`, adaptée au dépôt. Utilise la skill native `skill-creator` quand elle est disponible; sinon, écris directement les fichiers autonomes minimaux.

## 1. Interroger le dépôt, pas l'utilisateur

Réponds à ceci depuis le codebase et demande seulement à l'utilisateur ce que tu ne peux pas observer :

- **Surface :** qu'est-ce qu'un utilisateur touche réellement? Une UI web, une CLI/TUI, une app desktop, une API, une app mobile, une bibliothèque? Un dépôt peut en avoir plusieurs; choisis la principale et note le reste.
- **Exécution :** comment l'app démarre-t-elle localement? Préfère la commande de dev documentée par le dépôt lui-même (scripts package, Makefile, démarrage rapide du README). Note ports, variables d'environnement, données de seed, auth.
- **Pilotage :** comment un agent peut-il interagir avec elle par programme? Harnais existants d'abord : specs Playwright/Cypress, scripts expect, helpers PTY, endpoints utilisables avec curl, port de debug. Ensuite seulement, choisis une recette générique : navigateur/CDP pour web et Electron, harnais tmux/PTY pour CLI/TUI, HTTP simple pour les services.
- **Observation :** quelles preuves peuvent être capturées? Captures d'écran, transcriptions terminal, corps de réponse, logs, codes de sortie, état DB.
- **Isolation :** deux instances peuvent-elles tourner côté à côté (ports, répertoires de données, profils)? Sinon, dis-le dans la skill générée : refuser de piloter deux fois une instance partagée vaut mieux que corrompre la session de l'utilisateur.

Si le checkout ne build pas ou ne démarre pas tel quel, corrige ça d'abord (ou signale-le précisément) avant de générer; une skill écrite contre une base cassée enseigne les mauvaises étapes. Quand un asset manquant non pertinent bloque le démarrage (un répertoire statique que l'API ne sert jamais, une config exemple), la skill générée peut le créer, clairement marqué comme échafaudage de vérification, et le retirer au nettoyage.

## 2. Générer la skill

Écris `.agents/skills/verify-<app>/SKILL.md` avec un frontmatter YAML (`name: verify-<app>` et une `description` qui nomme l'app, la surface et quand l'utiliser) et ces sections, chacune fondée sur ce que l'interrogation a vraiment trouvé (aucun placeholder restant) :

- **Launch :** la commande exacte qui démarre l'app pour vérification, et comment savoir qu'elle est prête (ligne de log, port qui répond, prompt). Inclus le teardown. Pour une CLI ou TUI à courte durée, il n'y a pas de serveur à garder vivant : lancer signifie builder le binaire (ou installer les deps) une fois, puis démarrer chaque pilotage dans sa propre session PTY ou tmux isolée.
- **Doctor :** une vérification en lecture seule qui répond à "cette instance vaut-elle d'être pilotée?" : processus actif, bonne version/build, port possédé par nous, auth valide. Un agent l'exécute d'abord chaque fois que quelque chose semble anormal.
- **Drive :** la recette du harnais avec de vrais sélecteurs/commandes de ce dépôt, pas des exemples. Préfère les poignées stables (libellés ARIA, attributs data, chaînes de prompt, chemins de route) aux coordonnées et à l'ordre des onglets.
- **Preuve :** quoi capturer comme preuve et où ça va. Énonce les standards de preuve : exercer le vrai parcours utilisateur, pas des setters internes ou des endpoints réservés aux tests; capturer l'action et l'état résultant, pas seulement l'écran final; vérifier les effets de bord (fichiers écrits, lignes insérées, messages envoyés) avec ce qui est visible; mocks seulement lorsqu'une frontière de production isole déjà le système externe. Quand le chemin sûr est un dry-run ou un mode test, vérifie ce qu'il saute vraiment par observation (fichiers, réseau, refs git) au lieu de faire confiance à son nom : certains dry-runs touchent quand même le réseau ou ouvrent un navigateur.
- **Cleanup :** comment arrêter les instances créées par l'exécution. Ne tue jamais par nom de processus; tue ce que tu as démarré. Le nettoyage retire les instances et l'état temporaire, jamais les preuves : les artefacts de preuve survivent au teardown, dans un emplacement nommé par la skill.
- **Helpers :** tout script livré par la skill est exécutable et son invocation est montrée dans le corps de la skill. Un helper que le lecteur doit rétroconcevoir n'est pas un helper.

## 3. Amorcer la carte des fonctionnalités

Crée `.agents/skills/verify-<app>/features/README.md` plus un fichier par fonctionnalité visible par l'utilisateur que tu peux identifier (vise les 3 à 5 principales pour commencer, depuis les routes, commandes, menus ou docs). Suis la forme dans [`references/feature-map-example/`](references/feature-map-example/), avec un index README et un fichier par fonctionnalité. Chaque fichier répond, du point de vue de l'utilisateur : ce qu'est la fonctionnalité, comment y accéder, comment la piloter avec le harnais et quel état final observable prouve qu'elle fonctionne. Les quatre H2 sont `Sous-fonctionnalités`, `Comment y accéder (point de vue utilisateur)`, `Pilotage avec <harness>` et `Pièges`. La carte est la source de vérification maintenue du dépôt; une preuve qui pilote un seul point d'entrée pratique est incomplète quand la carte en liste d'autres.

## 4. Prouver la skill générée avant de la remettre

Exécute ses propres consignes de bout en bout une fois : launch, doctor, piloter UNE fonctionnalité cartographiée (une suffit; la carte existe pour que les exécutions suivantes couvrent le reste), capturer les preuves, nettoyer. Après nettoyage, confirme que les preuves existent encore à l'emplacement nommé : un nettoyage qui mange la preuve échoue cette étape. Corrige ce qui échoue et lance aussi le nettoyage généré après chaque itération échouée, pour que les tentatives cassées ne laissent pas traîner des processus et ports. Une skill générée qui n'a jamais été exécutée est un brouillon, pas un livrable.

## 5. Proposer la boucle de maintenance

Oriente l'utilisateur vers `$cstack:maintain-verification-skill` pour garder la carte fidèle quand l'app change. Suggère une cadence seulement s'il la demande.
