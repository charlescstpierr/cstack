# Vérifier le chargeur installé

Le workflow `installed-loader.yml` teste le plugin via Codex CLI 0.166.0 dans un runner GitHub hébergé vierge. Il utilise le HOME réel du compte sans le redéfinir et refuse tout profil `.codex` préexistant, toute redirection `CODEX_HOME` et toute clé de modèle. Le CLI et ses dépendances natives sont épinglés avec leurs intégrités npm sous `RUNNER_TEMP`.

Le test appelle `install.sh install --local`, `doctor`, une réapplication, `update` et `uninstall`. Il interroge `plugin/list` et `skills/list` avec le protocole IPC du CLI depuis un dossier temporaire extérieur au checkout. Il exige les 29 skills dans le cache installé, leur propriétaire et version, les octets des fichiers du paquet et leurs bits exécutables. Il vérifie aussi la conservation de la configuration et d'un fichier témoin du job.

Aucun login, tour de modèle ou changement de modèle n'est demandé. Le test utilise seulement l'authentification Git déjà fournie au checkout CI pour le contrôle d'accès au dépôt. Aucun credential n'est lu, copié ou publié. Le reçu JSON est limité aux assertions et empreintes ; les réponses IPC et stderr bruts ne sont pas publiés.

Une installation qui exige une interaction ou un compte connecté reste `blocked`. Aucun secret ne doit être ajouté pour masquer ce résultat. Les tests unitaires et le refus local du script ne prouvent pas une installation réussie. La [documentation officielle](https://developers.openai.com/plugins/build/plugins) précise que les comportements du chargeur varient selon le client.

Une réussite du job établirait le chargement installé par ce CLI, pas l'installation dans T3 App, l'activation d'une tâche ordinaire, le transport vers un modèle ou une supériorité comparative. Le job publie `installed-loader-evidence/receipt.json` pour examiner le résultat réel. Le premier résultat CI reste à obtenir.

```sh
python3 -B -m unittest discover -s tests -p test_installed_loader.py
```

L'exécution réelle du script est réservée au job CI ; elle refuse le profil humain local avant toute commande Codex. L'installateur existant peut utiliser un profil jetable lors d'un changement de source. Le wrapper du test refuse cette redirection et conserve alors un résultat bloqué au lieu de lancer le CLI sous un autre HOME.
