import type * as T from "./types.ts";
export const renderJson = (verdict: T.WatcherVerdict): string =>
  `${JSON.stringify(verdict)}\n`;
function ciCell(row: T.PrSnapshot): string {
  if (row.kind !== "open") return "\u2014";
  const was = row.ci.hadPreviousPassingCi ? ", était ✅" : "";
  switch (row.ci.kind) {
    case "ci-clean":
      return "✅";
    case "ci-pending":
      return `⏳ ${row.ci.pending.length} en attente${was}`;
    case "ci-failing":
      return `❌ ${row.ci.failed.length} en échec${row.ci.pending.length ? `, ${row.ci.pending.length} en attente` : ""}${was}`;
    case "ci-github-rejected":
      return `❌ GitHub signale des checks en échec${was}`;
    default: {
      const exhaustive: never = row.ci;
      return exhaustive;
    }
  }
}
function reviewCell(row: T.PrSnapshot): string {
  if (row.kind !== "open") return "\u2014";
  const open = row.threads.length;
  return row.reviewAutomationRunning
    ? open
      ? `🤖 en cours, ${open} ouverts`
      : "🤖 en cours"
    : open
      ? `📝 ${open} ouverts`
      : row.facts.reviewDecision === "REVIEW_REQUIRED"
        ? "👀 revue requise"
        : "✅";
}
function mergeCell(row: T.PrSnapshot): string {
  if (row.kind === "merged") return "✅ fusionnee";
  if (row.kind === "closed") return "❌ fermee";
  if (row.facts.isDraft) return "⏸ brouillon";
  if (row.facts.reviewDecision === "CHANGES_REQUESTED")
    return "⚠️ changements demandes";
  return row.facts.mergeable === "CONFLICTING" ||
    row.facts.mergeStateStatus === "DIRTY" ||
    row.facts.mergeStateStatus === "CONFLICTING"
    ? "⚠️ conflit"
    : row.facts.mergeStateStatus === "BLOCKED"
      ? "⛔ bloquee"
      : "✅";
}
export function renderStatusTable(rows: T.NonEmpty<T.PrSnapshot>): string {
  const lines = ["| PR | CI | Revue | Fusion |", "| --- | --- | --- | --- |"];
  for (const row of rows) {
    const url = `https://github.com/${row.context.owner}/${row.context.repo}/pull/${row.context.number}`;
    lines.push(
      `| [#${row.context.number}](${url}) | ${ciCell(row)} | ${reviewCell(row)} | ${mergeCell(row)} |`
    );
  }
  return `${lines.join("\n")}\n`;
}
function threadLine(thread: T.ReviewThread): string {
  const comment = thread.firstComment;
  return [
    thread.id,
    comment?.path ?? "None",
    comment?.line ?? "None",
    comment?.authorLogin ?? "None",
    `isBugBot=${thread.isBugbot}`,
    `bugbotReviewPasses=${thread.bugbotReviewPasses}`,
    (comment?.body ?? "").split(/\r?\n/, 1)[0]?.slice(0, 180) ?? "",
  ].join(" ");
}
type StatusQueryBlocker = {
  readonly kind: "status-query";
  readonly failures: number;
  readonly failure: { readonly detail: string };
};
function renderBlocker(blocker: T.MergeBlocker | StatusQueryBlocker): string {
  switch (blocker.kind) {
    case "merge-conflicts":
      return [
        "BLOCKER: merge-conflicts",
        `pr=${blocker.pr.number}`,
        `mergeable=${blocker.facts.mergeable}`,
        `mergeStateStatus=${blocker.facts.mergeStateStatus}`,
        "action=résoudre les conflits de fusion avant d’attendre la CI",
      ].join("\n");
    case "review-threads":
      return [
        "BLOCKER: review-threads",
        `pr=${blocker.pr.number}`,
        `unresolved=${blocker.threads.length}`,
        ...blocker.threads.map(threadLine),
      ].join("\n");
    case "failing-checks": {
      const failed = blocker.ci.kind === "ci-failing" ? blocker.ci.failed : [];
      const details = failed.map(
        (check) =>
          `${check.name} ${check.reportedState} ${check.description} ${check.link}`
      );
      if (blocker.ci.kind === "ci-github-rejected")
        details.push(
          `mergeStateStatus=${blocker.ci.github.mergeStateStatus}`,
          `headRollupState=${blocker.ci.github.headRollupState}`
        );
      return [
        "BLOCKER: failing-checks",
        `pr=${blocker.pr.number}`,
        `failed=${failed.length}`,
        ...details,
      ].join("\n");
    }
    case "merge-gate": {
      const action =
        blocker.reason === "closed-without-merge"
          ? "restaurer ou retirer la PR fermee de la pile en file"
          : blocker.reason === "draft-pr"
            ? "marquer la PR prête pour revue avant d’attendre la file de fusion"
            : blocker.reason === "review-required"
              ? "obtenir la revue d’approbation requise"
              : blocker.reason === "merge-blocked"
                ? "trouver la règle de protection de branche qui retient la fusion (mergeStateStatus=BLOCKED avec une CI propre)"
                : "résoudre la revue demandant des changements avant d’attendre la file de fusion";
      return [
        `BLOCKER: ${blocker.reason}`,
        `pr=${blocker.pr.number}`,
        `action=${action}`,
      ].join("\n");
    }
    case "status-query":
      return [
        "BLOCKER: status-query",
        `failures=${blocker.failures}`,
        `detail=${blocker.failure.detail}`,
        "action=vérifier le contexte de PR courant, l’authentification GitHub et la disponibilité de l’API, puis réarmer",
      ].join("\n");
    default: {
      const exhaustive: never = blocker;
      return exhaustive;
    }
  }
}
export function renderPretty(verdict: T.WatcherVerdict): string {
  switch (verdict.kind) {
    case "QUEUE":
      return `QUEUE: ${verdict.queue.length} PR capturee${verdict.queue.length === 1 ? "" : "s"} du bas vers le haut: ${verdict.queue.map((pr) => `#${pr.number}`).join(",")}\n`;
    case "STATUS":
      return renderStatusTable(verdict.rows);
    case "WAITING":
      return verdict.reason.kind === "pending-checks"
        ? `WAITING: frontier=#${verdict.frontier.number}; ${verdict.reason.pending.length} check${verdict.reason.pending.length === 1 ? "" : "s"} en attente\n`
        : `WAITING: frontier=#${verdict.frontier.number} sans bloqueur; attente de la file de fusion (${verdict.reason.unmergedCount} PR non fusionnee${verdict.reason.unmergedCount === 1 ? "" : "s"})\n`;
    case "ADVANCE":
      return `ADVANCE: #${verdict.merged.number} fusionnee; suivante=#${verdict.frontier.number}; restantes=${verdict.remaining}\n`;
    case "RETRY":
      return `RETRY: la requête de statut GitHub a échoué; nouvelle tentative dans ${verdict.retryInSeconds}s\ndetail=${verdict.failure.detail}\n`;
    case "BLOCKER":
      return `${renderBlocker(verdict.blocker)}\n`;
    case "READY": {
      const detail =
        verdict.scope.kind === "single" && verdict.scope.pr.kind === "ready-pr"
          ? `\nmergeStateStatus=${verdict.scope.pr.proof.ci.github.mergeStateStatus}\nreviewDecision=${verdict.scope.pr.proof.gate.reviewDecision}\nisDraft=${verdict.scope.pr.proof.gate.draft === "draft-allowed"}${verdict.scope.pr.proof.gate.draft === "draft-allowed" ? "\nnote=brouillon autorisé (--allow-draft); laisser en brouillon, ne pas marquer prêt" : ""}`
          : "";
      return `READY: aucun conflit de fusion, aucun fil de revue non résolu, aucun check en échec ou en attente${detail}\n`;
    }
    case "COMPLETE":
      return `COMPLETE: pile en file fusionnee (${verdict.queue.length} PR)\n`;
    case "TIMEOUT":
      if (verdict.reason.kind === "pending-checks")
        return "TIMEOUT: checks encore en attente\n";
      if (verdict.reason.kind === "status-unavailable")
        return "TIMEOUT: le statut GitHub est resté indisponible\n";
      return `TIMEOUT: la pile en file a encore ${verdict.reason.unmergedCount} PR non fusionnee${verdict.reason.unmergedCount === 1 ? "" : "s"}; frontier=#${verdict.reason.frontier.number}\n`;
    default: {
      const exhaustive: never = verdict;
      return exhaustive;
    }
  }
}
