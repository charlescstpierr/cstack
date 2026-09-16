# Encoder les leçons dans la structure

Lisez cette référence lorsqu'un processus cstack actif vous route ici ou lorsque l'utilisateur nomme ce principe. Suivez le [contrat d'exécution Codex](../codex-runtime.md) pour le périmètre et les permissions.

Encodez les correctifs récurrents dans des mécanismes (outils, code, métadonnées, automatisation) plutôt que dans des instructions textuelles. Chaque erreur, correction humaine et résultat inattendu est un signal d'apprentissage. Capturez-le, routez-le et fermez la boucle.

**Pourquoi :** les instructions textuelles sont faciles à manquer. Elles exigent que le lecteur remarque, se souvienne et obéisse. Les mécanismes structurels (règles de lint, drapeaux de métadonnées, contrôles à l'exécution, scripts d'automatisation) imposent la règle sans coopération.

**Motif :**
Lorsque vous vous surprenez à écrire la même instruction une deuxième fois :
1. Demandez : cela peut-il être une règle de lint, un drapeau de métadonnées, un contrôle à l'exécution ou un script ?
2. Si oui, encodez-le. Supprimez l'instruction
3. Si non (jugement requis), rendez l'instruction plus visible et ajoutez un exemple du mode d'échec

**Choisissez le mécanisme le plus fort.** Lorsque plusieurs mécanismes fonctionneraient, choisissez le plus fort que la situation permet (un état irreprésentable qui ne peut pas compiler, puis un lint ou une API interdite qui fait échouer la CI, puis un assistant canonique, puis un contrôle à l'exécution), parce que les agents copient ce que le code environnant fait déjà et qu'une garde plus faible devient le prochain modèle.

**Corollaire :** si le correctif est structurel, utilisez seulement le correctif structurel. L'instruction est le symptôme.

**Boucle de rétroaction :**
- **Capturez chaque correction.** Quand l'humain intervient ou que les tests échouent, décidez si c'est un cas isolé ou un motif.
- **Routez vers la bonne couche.** Cas isolé -> note mentale. Correctif récurrent -> compétence ou règle de lint. Problème systémique -> principe.
- **Fermez la boucle.** Ne vous contentez pas d'enregistrer. Appliquez maintenant ou créez une tâche concrète.

**Anti-motifs :**
- Accuser réception sans enregistrer (« je vais garder ça en tête » ne persiste pas)
- Enregistrer sans router (une note mentale sur une règle de lint qui devrait exister est gaspillée si la règle n'est pas implémentée)
- Corriger sans généraliser (corriger une instance tout en laissant le motif récurrent intact)
