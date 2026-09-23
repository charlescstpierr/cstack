import { expect, it } from "bun:test";
import { spawnSync } from "node:child_process";
import {
  chmodSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { object } from "./landing.ts";

function fixture(
  body: (
    run: (...args: string[]) => {
      status: number | null;
      output: Record<string, unknown>;
    },
    file: string,
    directory: string
  ) => void
) {
  const directory = mkdtempSync(join(tmpdir(), "cstack-shipping-cli-"));
  const file = join(directory, "state.json");
  writeFileSync(
    file,
    JSON.stringify({
      id: "pr-id",
      state: "OPEN",
      headRefOid: "head",
      baseRefName: "main",
      baseRefOid: "base",
      autoMergeRequest: { enabledAt: "now" },
      mergeQueueEntry: { id: "queue" },
      mergeCommit: null,
    })
  );
  const gh = join(directory, "gh");
  writeFileSync(
    gh,
    `#!${process.execPath}
import { readFileSync, writeFileSync } from 'node:fs';
const state = JSON.parse(readFileSync(process.env.SHIPPING_STATE, 'utf8'));
const args = process.argv.slice(2);
const query = args.find(arg => arg.startsWith('query=')) ?? '';
let result;
if (query.includes('disablePullRequestAutoMerge')) {
  if (!query.includes('disablePullRequestAutoMerge(input:{pullRequestId:$id})')) throw new Error('wrong auto-merge input');
  state.autoMergeRequest = null;
  result = { disablePullRequestAutoMerge: { clientMutationId: null } };
} else if (query.includes('dequeuePullRequest')) {
  if (!query.includes('dequeuePullRequest(input:{id:$id})')) throw new Error('wrong queue input');
  state.mergeQueueEntry = null;
  result = { dequeuePullRequest: { clientMutationId: null } };
} else result = { repository: { pullRequest: state } };
writeFileSync(process.env.SHIPPING_STATE, JSON.stringify(state));
console.log(JSON.stringify({ data: result }));
`
  );
  chmodSync(gh, 0o755);
  const entry = join(directory, "entry.ts");
  writeFileSync(
    entry,
    `import { main } from ${JSON.stringify(
      join(import.meta.dir, "shipping-cli.ts")
    )}; process.exitCode = await main(process.argv.slice(2));`
  );
  const run = (...args: string[]) => {
    const result = spawnSync(process.execPath, [entry, ...args], {
      encoding: "utf8",
      timeout: 3_000,
      env: {
        ...process.env,
        PATH: `${directory}:${process.env.PATH}`,
        SHIPPING_STATE: file,
      },
    });
    return {
      status: result.status,
      output: object(JSON.parse(result.stdout), "résultat CLI"),
    };
  };
  try {
    body(run, file, directory);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

it("inspecte, sauvegarde, annule et relit les deux mécanismes dans des processus séparés", () =>
  fixture((run, file, directory) => {
    const inspected = run("inspect", "--repo", "owner/repo", "--pr", "1");
    expect(inspected.status).toBe(0);
    expect(object(inspected.output.record, "record").revision).toEqual({
      context: { owner: "owner", repo: "repo", number: 1 },
      headRefOid: "head",
      baseRefName: "main",
      baseRefOid: "base",
    });
    const saved = join(directory, "record.json");
    writeFileSync(saved, JSON.stringify(inspected.output));
    const cancelled = run("cancel-pending", "--record", saved);
    expect(cancelled.status).toBe(0);
    expect(cancelled.output).toMatchObject({
      kind: "cancelled",
      record: { pending: { autoMerge: false, queueEntryId: null } },
    });
    expect(JSON.parse(readFileSync(file, "utf8"))).toMatchObject({
      autoMergeRequest: null,
      mergeQueueEntry: null,
    });
  })
);

it("refuse une base changée sans annuler quoi que ce soit", () =>
  fixture((run, file, directory) => {
    const inspected = run("inspect", "--repo", "owner/repo", "--pr", "1");
    const saved = join(directory, "record.json");
    writeFileSync(saved, JSON.stringify(inspected.output));
    const changed = {
      ...JSON.parse(readFileSync(file, "utf8")),
      baseRefOid: "advanced",
    };
    writeFileSync(file, JSON.stringify(changed));
    const result = run("cancel-pending", "--record", saved);
    expect(result.status).toBe(1);
    expect(result.output.kind).toBe("changed");
    expect(JSON.parse(readFileSync(file, "utf8"))).toEqual(changed);
  })
);

it("traite un champ queue manquant comme unavailable", () =>
  fixture((run, file) => {
    const raw = JSON.parse(readFileSync(file, "utf8"));
    delete raw.mergeQueueEntry;
    writeFileSync(file, JSON.stringify(raw));
    const result = run("inspect", "--repo", "owner/repo", "--pr", "1");
    expect(result.status).toBe(1);
    expect(result.output.kind).toBe("unavailable");
  })
);
