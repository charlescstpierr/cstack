# Sécurité de fusion et de restack

Utilisez cette référence avec [Expédition](../playbooks/shipping.md) et
[Autopilot-stack](../playbooks/autopilot-stack.md) avant toute réécriture,
retarget ou fusion. Le watcher garde la classification des contrôles; ces
opérations ajoutent des vérifications de révision et de destination sans
accorder l'autorité de fusion.

## Lire et annuler les deux mécanismes pending

Utilisez `ship-pr` sous `skills/cstack/scripts/watch-pr/`. Il possède le
transport GitHub, le parsing, l'ordre des mutations et le readback. Le watcher
reste un lecteur de contrôles; seul `ship-pr` lit et conserve la révision
complète composée du dépôt, de la PR, du head, du nom de base et du SHA de
base.

```sh
bash <plugin-root>/scripts/run-tool.sh watch-pr/ship-pr inspect \
  --repo "$owner/$repo" --pr "$pr" > "$record_file"
bash <plugin-root>/scripts/run-tool.sh watch-pr/ship-pr cancel-pending \
  --record "$record_file"
```

`inspect` produit un enregistrement avec l'état de la PR, le commit de merge,
`autoMergeRequest` et `mergeQueueEntry`. `cancel-pending` relit la révision
courante, désactive auto-merge s'il est actif, relit la file, la retire si elle
reste active, puis relit les deux mécanismes. Une sortie `cancelled` est la
seule sortie qui autorise la réécriture de topologie. `changed`, `not-open`,
`still-pending` et `unavailable` ferment la branche d'action; des champs
manquants ou une API non disponible ne signifient jamais « absent ».

Inspectez et annulez chaque PR touchée par une réécriture, y compris ses
descendants dont la base va changer. Laissez les PR sans dépendance intactes.
`cancel-pending` compare le pending du reçu avant sa première mutation et
relit la file juste avant un dequeue; une entrée remplacée ou réarmée devient
`changed`. L'annulation est un état observé, pas un verrou : l'API GitHub
accepte seulement l'ID de la PR pour `dequeuePullRequest` et ne fournit pas de
CAS sur `queueEntryId`. Une course après le dernier readback reste possible;
un unique propriétaire de topologie doit donc sérialiser l'opération et
réconcilier tout état concurrent.

## Préserver les écritures concurrentes et la frontière enfant

Avant toute réécriture, capturez le SHA distant exact :

```sh
git ls-remote --exit-code origin "refs/heads/$branch"
```

Validez que la réponse désigne exactement cette ref et conservez le SHA dans la
preuve. Une ref de suivi après `fetch` ne constitue pas un lease.

Après le squash du parent, gardez son ancien tip comme frontière de l'enfant,
vérifiez qu'il est ancêtre de l'enfant et inspectez la plage avant de rebaser :

```sh
git merge-base --is-ancestor "$old_parent_tip" "$child"
git rebase --onto "$trunk_tip" "$old_parent_tip" "$child"
git push --force-with-lease="refs/heads/$child:$captured_remote_head" \
  origin "HEAD:refs/heads/$child"
```

Exécutez le rebase dans le worktree propre de l'enfant. La plage
`old_parent_tip..child` doit contenir uniquement le travail enfant; ne déduisez
jamais cette frontière du nouveau commit squash du parent. Si le lease refuse
la poussée, refaites une réconciliation; ne rafraîchissez pas le lease pour
écraser le travail concurrent.

## Garder la fusion liée au head exact

Pour une fusion GitHub immédiate, utilisez le head vérifié dans la condition du
service :

```sh
gh pr merge "$pr" --repo "$owner/$repo" --squash \
  --match-head-commit "$verified_head"
```

Cette condition protège le head, pas atomiquement la branche de base. Observez
la base immédiatement avant et après et coordonnez tout retarget concurrent.
`--auto` et l'admission en merge queue sont des actions futures : elles ne sont
acceptables qu'avec des règles de dépôt qui revérifient le verdict indépendant,
les contrôles requis et le contexte de la révision qui atterrira. Un contrôle
vert ou un verdict ancien ne suffit pas; n'utilisez jamais `--admin` pour
contourner la protection.

Après chaque merge, confirmez l'état `MERGED`, le head approuvé, la base prévue
et un commit de merge non nul. Fetch la destination, vérifiez que le commit de
merge est ancêtre de son tip et inspectez le contenu avant d'avancer vers la
PR suivante.
