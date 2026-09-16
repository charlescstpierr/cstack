# Portage de cstack

Cible approuvée : dépôt GitHub privé `charlescstpierr/cstack`, portage complet du commit `889ec4b68fa5aab0e867dad71ec3fdf386ae48f3` de `cursor/plugins/pstack` (pstack 0.15.2), Codex App et CLI, activation explicite avec `$cstack:cstack`, aucun moteur d'orchestration externe.

## Checklist de livraison

- [x] Empaqueter un plugin sous `plugins/cstack` et un marketplace de dépôt.
- [x] Comptabiliser les 47 compétences amont comme 23 références de principes plus les compétences spécialisées restantes, 23 guides d'exécution principaux, deux invites d'agents, le pack d'automatisation dormant et la compétence originale `deslop` (29 compétences dans le catalogue 0.4.0).
- [x] Porter le routeur et les guides d'exécution principaux vers les outils natifs, en préservant les limites de périmètre et d'autorisation.
- [x] Porter les compétences et références de support ; documenter explicitement les intégrations indisponibles.
- [x] Remplacer la résolution frontière de Graphite par git/gh ; préserver les portes de vérification du SHA de tête.
- [x] Préparer les scripts assistants dans un état de projet modifiable plutôt que de muter les caches de plugins.
- [x] Valider les manifestes, les métadonnées de compétences, les chemins de références et la couverture amont.
- [x] Exécuter les tests existants et ciblés, la vérification de types, une revue indépendante et des contrôles réalistes de compétences.
- [x] Publier en privé, vérifier une installation GitHub propre et la découverte dans une nouvelle session.

## Contrats partagés

- Répertoire/nom de la compétence principale : `cstack` ; compétence de configuration : `setup-cstack`. Les autres slugs de compétences restent inchangés et leurs descriptions utilisent la syntaxe Codex `$skill`.
- Toutes les politiques d'invocation de compétences sont explicites uniquement. Le routeur lit directement les chemins de compétences embarqués, relatifs à lui-même, quand un processus les demande.
- Chaque point d'entrée lie vers `skills/cstack/references/codex-runtime.md` avec un lien relatif. Ce contrat partagé décrit le choix des outils natifs et l'état local.
- Les rôles d'agents sont livrés comme invites Markdown sous les `references/agents` de la compétence principale ; transmettez leurs instructions aux sous-agents natifs disponibles. Ne supposez pas que des rôles nommés sont enregistrés.
- L'état vit sous `.cstack/` dans l'espace de travail cible, jamais dans un stockage Cursor ni dans le cache du plugin installé. Les surcharges de modèles utilisent `.cstack/models.json` : un objet qui associe les libellés de rôles amont à une chaîne de modèle ou, pour les comités, à une liste de chaînes. Les entrées manquantes et `inherit-parent` héritent ; validez les vrais noms de modèles dans la session courante. N'inventez pas d'API de liste de modèles. L'usage principal fonctionne sans configuration.
- Les assistants gardent Bun et les paquets amont verrouillés. La racine fournit `scripts/run-tool.sh`, qui prépare les sources fiables des assistants dans un nouveau répertoire temporaire sous `.cstack/tools/` à chaque invocation, y installe les dépendances verrouillées, exécute, puis nettoie. Les arguments et le cwd cible sont préservés. Les invocations parallèles ne partagent aucun état exécutable de l'espace de travail. Le cache ordinaire de paquets Bun évite les téléchargements répétés. Aucune installation dans le cache du plugin.
- Les processus GitHub utilisent git/gh. La résolution des piles suit les relations head/base des PR à partir de la branche courante, rejette les relations ambiguës, cycliques ou manquantes, et conserve la vérification du SHA de tête réel.
- Utilisez les continuations/attentes natives au premier plan. La reprise planifiée dépend d'un planificateur natif disponible et d'une demande explicite de l'utilisateur. Ne promettez pas que les agents locaux survivent à la fermeture de l'application. Le comportement Cursor cloud-only, l'interface de webhooks Grok et l'automatisation événementielle Benny sont des limites documentées, jamais des espaces réservés exécutables.
- Aucun message externe automatique, création de PR, fusion, publication, opération destructive ni édition de compétences sans rapport ne découle de la seule activation d'un mode. Respectez l'autorisation déjà donnée pour la tâche concrète.
- Le README et le bref guide utilisateur sont en français ; les instructions des compétences restent en anglais. Les docs d'exécution doivent être autonomes, sans plugin compagnon requis.

## Propriété d'exécution

- Racine : paquetage du plugin, contrat d'exécution partagé, lanceur inscriptible, configuration, validation, installation et publication.
- Voie des compétences de support : toutes les compétences sauf cstack et setup-cstack, y compris leurs ressources et scripts ; notices d'intégrations non prises en charge.
- Voie routeur : `SKILL.md` principal, guides d'exécution et références de la compétence principale sauf `codex-runtime.md` et les invites d'agents.
- Voie assistants : scripts de la compétence principale seulement, remplacement de Graphite et tests.

Les preuves de base et de vérification sont enregistrées dans `docs/VERIFICATION.md` une fois complètes. Ce plan est de la documentation, pas une dépendance d'exécution installée.

Décision après revue indépendante : les caches exécutables persistants locaux au projet peuvent être préremplis ou modifiés, dépendances et marqueurs de bootstrap inclus. Utilisez une préparation temporaire fraîche par invocation plutôt que de faire confiance à un répertoire de digest existant. Cela retire aussi la sérialisation entre exécutions d'assistants ; le coût est une installation de dépendances mise en cache par invocation.
