---
name: no-comments
description: "À utiliser pour $cstack:no-comments lors d'une revue indépendante des commentaires. Mène cette revue, corrige les constats acceptés et propose des encodages pour les contraintes déclarées."
---

# No comments

Runtime : [règles communes](../cstack/references/runtime/base.md), [délégation](../cstack/references/runtime/delegation.md), [orchestration](../cstack/references/runtime/orchestration.md).

Exécute une revue indépendante des commentaires, puis agis sur les constats acceptés. `deslop` (`../deslop/SKILL.md`) nettoie le slop du code, `unslop` (`../unslop/SKILL.md`) le nettoie de la prose, et `no-comments` confie les commentaires à un relecteur qui ne les a pas écrits.

## Portée

Utilise les fichiers ou le diff de l'appelant. Sinon, utilise le diff courant contre la branche de base, par défaut `main`, y compris le working tree.

## Étapes

1. Lis [`../cstack/references/agents/comment-reviewer.md`](../cstack/references/agents/comment-reviewer.md) et transmets ce prompt plus la portée à un sous-agent natif. L'assignation est en lecture seule; aucun rôle enregistré nommé n'est requis.
2. Inspecte son rapport. Rejette les échappées de portée, les suppressions protégées par exception et les signalements qui traitent des commentaires intentionnels comme coupables. Une conservation survit seulement avec preuve que la contrainte ne peut pas être exprimée en code. Audite les suppressions de lint bornées et TypeScript manquées. Les suppressions de correction ou de sécurité restent actionnables. Avant d'accepter des constats minces `IMPORTANT` ou `do not remove`, exécute `$cstack:how` ou `$cstack:why` sur le symbole. Relance une revue rejetée avec l'échec nommé. Si la seconde revue est encore rejetée, signale le problème comme ouvert et fais échouer `$cstack:no-comments`.
3. Corrige directement les constats triviaux acceptés en supprimant la narration morte, en retirant un contournement ou en utilisant la vraie API. Si un correctif exige une forme, exécute `$cstack:architect` une fois pour l'ensemble accepté et le code environnant. Arrête-toi à l'esquisse; l'étape 4 l'implémente.
4. Implémente le plus petit correctif de cause racine dans la portée. Retire chaque contournement nommé. Si la cause racine est hors portée, livre le plus petit correctif dans la portée et signale le reste ouvert. Les références [corriger les causes racines](../cstack/references/principles/fix-root-causes.md) et [reconcevoir depuis les premiers principes](../cstack/references/principles/redesign-from-first-principles.md) guident seulement l'intention. Aucune n'autorise l'élargissement de la clôture ni la correction d'instances hors de celle-ci. Ne boulonne jamais des gardes de symptôme.
5. Pour les commentaires de contrainte tels que `do not remove`, `do not change wording` ou `talk to X before changing`, laisse les contraintes prouvées concernant des choses hors du codebase. Propose le type, le contrôle d’exécution, test ou lint CI dans la portée le moins cher. Encode-le quand la tâche courante autorise cette édition; sinon, garde le commentaire prouvé et signale l'encodage possible.
6. Rapporte le nombre de suppressions, les commentaires restaurés, les relances, l'esquisse architect, les correctifs, les offres d'encodage, les encodages, les contraintes non appliquées et les autres travaux ouverts.
