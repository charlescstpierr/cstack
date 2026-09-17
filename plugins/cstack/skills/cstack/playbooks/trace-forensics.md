### Forensique de trace

Suivez [le contrat d’exécution Codex](../references/codex-runtime.md).

**Tu possèdes le diagnostic depuis l’artéfact. Charge-le, structure-le, réduis jusqu’à la cause, attribue à la source.**

Distinct de **Exécution forensics**, qui instrumente le processus vivant. Ici, la capture existe déjà. L’artéfact est un dataset fixe : lis-le, ne le relance pas. Garde l’outillage générique pour que le playbook reste portable : DevTools ou parseur de trace pour cpuprofile et `.json.gz`, éditeur texte pour un spindump, ton outillage heap pour un heapsnapshot.

1. Identifie le format et charge-le avec le bon outil. Parse les grands artéfacts dans un sous-agent (référence [Protéger la fenêtre de contexte](../references/principles/guard-the-context-window.md)) et garde le constat réduit dans le fil principal.
2. Transforme l’artéfact brut en forme interrogeable. Déverse la trace ou le heap snapshot dans sqlite, une ligne par sample, frame ou node. Atteins la forme interrogeable avant de lire.
3. Réduis jusqu’à la cause. Requête les frames qui détiennent le plus de temps et parcours l’arbre d’appels jusqu’au chemin chaud. Pour une fuite, suis la chaîne de rétention depuis l’objet fuité jusqu’à une racine GC. Pour un spindump, trouve le thread coincé on-CPU ou bloqué et sa raison d’attente.
4. Attribue à la source. Mappe la frame chaude vers fichier, symbole et ligne via les propres symboles de l’artéfact. Une frame sans mapping source n’est pas encore un diagnostic. Résous les symboles, ou dis clairement que l’artéfact ne les porte pas.
5. Confirme contre une capture appariée quand tu en as une. Diff un artéfact avant et après. Sans cela, marque le constat comme l’hypothèse la plus forte que l’artéfact soutient, pas comme cause confirmée.
6. Rends un diagnostic cité, pas de correctif sauf demande. Route vers Bug fix ou Perf issue une fois la cause connue. Le point de contrôle de débit reste sur une ligne : `throughput checkpoint: n/a, read-only forensics`.

**Réponse :** l’artéfact et le format, le constat réduit, l’emplacement source, les chemins d’artéfact et si une capture appariée l’a confirmé. Chaque affirmation porte sa preuve ou son étiquette dans la même phrase. Mesuré, inféré ou supposition. Une prédiction ou une cause non observée est une supposition. Ne remets jamais à l’humain un contrôle que tu pourrais lancer.
