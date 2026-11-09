# Notes pour le council de code

Relire le contrat consolidé `plugins/cstack/skills/cstack/references/runtime/t3.md` contre les exigences V5 de la demande. Le design n'est pas à rouvrir. Aucun sous-agent, push ou PR n'a été lancé par l'implémenteur.

Points à vérifier dans le code et les tests :

- `models.py` garde T3 hors des runtimes CLI, valide la forme entière et expose les blocages par rôle/position. Les champs inherited servent à construire target, jamais à inventer des clés delegate_task.
- Les métadonnées passées aux helpers établissent seulement une cohérence. La trace et les outils observés restent la responsabilité du coordinateur. Une preuve inaccessible bloque explicitement.
- `project.py` préserve les agents des rôles T3 avant toute décision de suppression ou de génération. Le préflight hors hôte bloque malgré ces agents.
- `prepare.ts` ne lance rien et ne découvre aucun outil. Le résultat `prepared` n'est pas une autorisation de dispatch. Le coordinateur doit comparer la cible avec le préflight courant.
- Le snapshot du helper porte le brief et ses fichiers de contexte. La transmission du commit ou la reconstitution du code dans le checkout reviewer et les contrôles HEAD/status restent à observer par le coordinateur.
- Le catalogue normalisé est volontairement limité à des options scalaires à valeurs déclarées. Une option plus complexe est non vérifiée, pas devinée. Pas de recommandation qualitative entre fournisseurs.
- Le setup T3 modèle seul passe par `models.py --host t3`. Le setup général `project.py` refuse les nouveaux choix T3 sans contexte de disponibilité et préserve les rôles T3 déjà enregistrés. Il ne doit pas servir à contourner ce refus.

Le rapport `docs/T3-VERIFICATION.md` sépare tests déterministes, observations rapportées par le parent et smoke restant à faire. Les garanties de confinement, chargement installé et backend effectif ne sont pas revendiquées.

La passe locale du diff a retiré le second parsing identique de sélection dans `project.py`. Les contrôles du rapport sont repassés après cette simplification. Aucune revue indépendante n'est revendiquée par l'auteur. La résolution du fallback natif est partagée par resolve et preflight via `role_value`; le test existant de mutation continue de viser une seule autorité.
