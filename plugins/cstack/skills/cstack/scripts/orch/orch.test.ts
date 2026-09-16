import { afterEach, describe, expect, it } from "bun:test";
import {
  chmod,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rm,
  symlink,
  writeFile,
} from "node:fs/promises";
import { existsSync, realpathSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  NotFoundError,
  UserError,
  openStore,
  parseVerdict,
  type OpenStoreOptions,
  type Store,
} from "./store.ts";

const SCRIPT = join(import.meta.dir, "orch.ts");
const WORKTREE_AUDIT = join(import.meta.dir, "..", "worktree-audit.sh");
const directories: string[] = [];
const handles: Store[] = [];

interface RunResult {
  readonly code: number;
  readonly stdout: string;
  readonly stderr: string;
}

async function makeDirectory(): Promise<string> {
  const directory = await mkdtemp(join(tmpdir(), "orch-test-"));
  directories.push(directory);
  return directory;
}

function useStore(
  directory: string,
  options?: OpenStoreOptions
): Store {
  const store = openStore(directory, options);
  handles.push(store);
  return store;
}

async function initializedStore(): Promise<{
  readonly directory: string;
  readonly store: Store;
}> {
  const directory = await makeDirectory();
  const store = useStore(directory);
  await store.init();
  return { directory, store };
}

function git({
  args,
  repo,
}: {
  args: readonly string[];
  repo: string;
}): string {
  const result = Bun.spawnSync(["git", "-C", repo, ...args]);
  if (result.exitCode !== 0) {
    throw new Error(
      `git ${args.join(" ")} failed: ${result.stderr.toString()}`
    );
  }
  return result.stdout.toString().trim();
}

async function makeGitStack(directory: string): Promise<{
  readonly repo: string;
  readonly mergedSha: string;
  readonly closedSha: string;
  readonly openSha: string;
}> {
  const repo = join(directory, "repo");
  await mkdir(repo);
  git({ repo, args: ["init", "--initial-branch=main"] });
  git({ repo, args: ["config", "user.name", "Orch Test"] });
  git({ repo, args: ["config", "user.email", "orch@example.com"] });
  await writeFile(join(repo, "main.txt"), "main\n");
  git({ repo, args: ["add", "."] });
  git({ repo, args: ["commit", "-m", "main"] });

  const branches = ["stack/merged", "stack/closed", "stack/open"];
  for (const [index, branch] of branches.entries()) {
    git({ repo, args: ["checkout", "-b", branch] });
    await writeFile(join(repo, `stack-${index}.txt`), `${branch}\n`);
    git({ repo, args: ["add", "."] });
    git({ repo, args: ["commit", "-m", branch] });
  }

  return {
    repo,
    mergedSha: git({ repo, args: ["rev-parse", "stack/merged"] }),
    closedSha: git({ repo, args: ["rev-parse", "stack/closed"] }),
    openSha: git({ repo, args: ["rev-parse", "stack/open"] }),
  };
}

async function withFakeGh<T>({
  directory,
  operation,
  output,
}: {
  directory: string;
  operation: (outputPath: string) => Promise<T>;
  output: string;
}): Promise<T> {
  const bin = join(directory, "bin");
  const outputPath = join(directory, "gh-output.json");
  await mkdir(bin);
  await writeFile(outputPath, output);
  const gh = join(bin, "gh");
  await writeFile(
    gh,
    `#!/usr/bin/env bash
set -euo pipefail
if [ "$(pwd -P)" != "${realpathSync(join(directory, "repo"))}" ]; then
  printf 'gh ran outside the fixture repo: %s\\n' "$(pwd -P)" >&2
  exit 2
fi
case "$*" in
  "repo view --json defaultBranchRef")
    printf '{"defaultBranchRef":{"name":"main"}}\\n'
    ;;
  "pr list --state all --limit 1000 --json number,state,headRefName,baseRefName,headRefOid")
    cat "${outputPath}"
    ;;
  *)
    printf 'unexpected gh arguments: %s\\n' "$*" >&2
    exit 2
    ;;
esac
`
  );
  await chmod(gh, 0o755);

  const originalPath = process.env.PATH;
  process.env.PATH = `${bin}:${originalPath ?? ""}`;
  try {
    return await operation(outputPath);
  } finally {
    if (originalPath === undefined) {
      delete process.env.PATH;
    } else {
      process.env.PATH = originalPath;
    }
  }
}

function runCli(
  args: readonly string[],
  env: Readonly<Record<string, string | undefined>> = process.env
): RunResult {
  const result = Bun.spawnSync([process.execPath, SCRIPT, ...args], { env });
  return {
    code: result.exitCode,
    stdout: result.stdout.toString(),
    stderr: result.stderr.toString(),
  };
}

afterEach(async () => {
  for (const store of handles.splice(0).reverse()) {
    await store.close();
  }
  for (const directory of directories.splice(0)) {
    await rm(directory, { recursive: true, force: true });
  }
});

describe("Magasin", () => {
  it("initialise un magasin de fichiers idempotent et libère son verrou", async () => {
    const directory = await makeDirectory();
    const store = useStore(directory);

    expect(await store.init()).toEqual({ store: directory });
    const firstUnits = await readFile(join(directory, "units.tsv"), "utf8");
    const firstLedger = await readFile(
      join(directory, "ledger.tsv"),
      "utf8"
    );

    expect(await store.init()).toEqual({ store: directory });
    expect(await readFile(join(directory, "units.tsv"), "utf8")).toBe(
      firstUnits
    );
    expect(await readFile(join(directory, "ledger.tsv"), "utf8")).toBe(
      firstLedger
    );
    expect((await readdir(directory)).sort()).toEqual([
      ".orch.lock",
      "frontier.json",
      "gates.md",
      "inbox",
      "ledger.tsv",
      "preferences.md",
      "units.tsv",
    ]);

    await store.close();
    expect(await readdir(directory)).not.toContain(".orch.lock");
  });

  it("compose ajout, mise à jour, lecture, liste et comptes d’unité", async () => {
    const { store } = await initializedStore();

    expect(
      await store.units.add({
        id: "u1",
        track: "build",
        brief: "briefs/u1.md",
      })
    ).toMatchObject({ id: "u1", state: "pending" });
    expect(
      await store.units.add({ id: "=SUM(A1)", track: "+build" })
    ).toMatchObject({ id: "'=SUM(A1)", track: "'+build" });

    const updated = await store.units.set({
      id: "u1",
      state: "done",
      branch: "cstack/u1",
      pr: 184530,
      sha: "abc123",
    });
    expect(updated).toEqual({
      id: "u1",
      track: "build",
      state: "done",
      branch: "cstack/u1",
      pr: "184530",
      sha: "abc123",
      brief: "briefs/u1.md",
    });
    expect(await store.units.get("u1")).toEqual(updated);
    expect(
      await store.units.list({ state: "done", track: "build" })
    ).toEqual([updated]);
    expect(await store.units.counts()).toEqual({ done: 1, pending: 1 });
    await expect(
      store.units.add({ id: "u1", track: "build" })
    ).rejects.toThrow("l’unité u1 existe déjà");
    await expect(
      store.units.set({ id: "missing", state: "done" })
    ).rejects.toBeInstanceOf(NotFoundError);
  });

  it("enregistre, remplace, vérifie et résume les verdicts types du registre", async () => {
    const { store } = await initializedStore();

    try {
      await store.ledger.check({ pr: 184530, sha: "abc123" });
      throw new Error("verification du registre attendue en echec");
    } catch (error) {
      expect(error).toBeInstanceOf(NotFoundError);
      if (error instanceof NotFoundError) {
        expect(error.output).toEqual({
          compact: "NOT-VERIFIED",
          json: {
            pr: "184530",
            sha: "abc123",
            verdict: "NOT-VERIFIED",
          },
        });
      }
    }
    expect(() => parseVerdict("looks-good")).toThrow("le verdict doit être");

    const recorded = await store.ledger.record({
      pr: 184530,
      sha: "abc123",
      verdict: "unit-test-verified",
      evidence: "reports/verify.md",
      verifier: "sol",
    });
    expect(await store.ledger.check({ pr: 184530, sha: "abc123" })).toEqual(
      recorded
    );
    expect(await store.ledger.summary()).toEqual({
      "unit-test-verified": 1,
    });

    await store.ledger.record({
      pr: 184530,
      sha: "abc123",
      verdict: "live-ui-verified",
      evidence: "reports/live.md",
    });
    expect(await store.ledger.summary()).toEqual({
      "live-ui-verified": 1,
    });
  });

  it("ajoute, consulte et vide atomiquement les pointeurs de boîte de réception", async () => {
    const { directory, store } = await initializedStore();

    const first = await store.inbox.push({
      agent: "worker-1",
      unit: "u1",
      status: "done",
      report: "reports/u1.md",
    });
    expect(first.pointer).toMatchObject({ unit: "u1", status: "done" });
    expect(first.filename).toEndWith(".tsv");
    await store.inbox.push({
      agent: "worker-2",
      unit: "u2",
      status: "failed",
    });

    expect(await store.inbox.count()).toBe(2);
    expect(await store.inbox.peek()).toHaveLength(2);
    expect(await store.inbox.count()).toBe(2);
    expect(await store.inbox.drain()).toHaveLength(2);
    expect(await store.inbox.count()).toBe(0);
    expect(await readdir(join(directory, "inbox"))).toEqual([]);
    expect(
      (await readdir(directory)).filter((name) =>
        name.startsWith(".inbox-drain-")
      )
    ).toEqual([]);
  });

  it("ajoute des pointeurs de boîte de réception sans prendre le verrou du magasin", async () => {
    const { directory, store } = await initializedStore();
    const other = useStore(directory);
    const results = await Promise.all([
      other.inbox.push({ agent: "a", unit: "u1", status: "done" }),
      other.inbox.push({ agent: "b", unit: "u2", status: "done" }),
      store.inbox.push({ agent: "c", unit: "u3", status: "done" }),
    ]);
    expect(results).toHaveLength(3);
    expect(await store.inbox.count()).toBe(3);
  });

  it("refuse de vider un répertoire non initialisé", async () => {
    const directory = await makeDirectory();
    const inbox = join(directory, "inbox");
    await mkdir(inbox);
    await writeFile(join(inbox, "keep.txt"), "secret\n");
    const store = useStore(directory);
    await expect(store.inbox.drain()).rejects.toThrow(
      "le magasin n'est pas initialise"
    );
    expect(await readFile(join(inbox, "keep.txt"), "utf8")).toBe("secret\n");
    expect(await readdir(inbox)).toEqual(["keep.txt"]);
  });

  it("vide seulement les pointeurs de boîte de réception parsés et laisse les autres entrées", async () => {
    const { directory, store } = await initializedStore();
    await store.inbox.push({
      agent: "worker-1",
      unit: "u1",
      status: "done",
    });
    await writeFile(join(directory, "inbox", "notes.md"), "keep\n");
    expect(await store.inbox.drain()).toHaveLength(1);
    expect(await readdir(join(directory, "inbox"))).toEqual(["notes.md"]);
  });

  for (const format of ["fichier PID", "répertoire"] as const) {
    it(`laisse un seul processus reprendre un verrou périmé (${format})`, async () => {
      const { directory, store } = await initializedStore();
      await store.close();
      const exited = Bun.spawn(["true"]);
      await exited.exited;
      const lock = join(directory, ".orch.lock");
      if (format === "fichier PID") {
        await writeFile(lock, `${exited.pid}\n`);
      } else {
        await mkdir(lock);
        await writeFile(join(lock, `owner.${exited.pid}.${randomUUID()}`), "");
      }

      const worker = join(directory, "takeover-worker.ts");
      await writeFile(
        worker,
        `import { existsSync, writeFileSync } from "node:fs";
  import { join } from "node:path";
  import { openStore } from ${JSON.stringify(join(import.meta.dir, "store.ts"))};
  const storeDir = ${JSON.stringify(directory)};
  const id = process.argv[2];
  const handle = openStore(storeDir, { onStaleLock() {
    writeFileSync(join(storeDir, "ready-" + id), "");
    const deadline = Date.now() + 10000;
    while (!existsSync(join(storeDir, "go-" + id))) {
      if (Date.now() > deadline) throw new Error("délai de coordination dépassé");
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 5);
    }
  }});
  try {
    await handle.units.add({ id: "u-" + process.pid, track: "build" });
    writeFileSync(join(storeDir, "result-" + id), "WON");
  } catch (error) {
    writeFileSync(join(storeDir, "result-" + id), "LOST: " + error.message);
    process.exitCode = 1;
  } finally {
    const deadline = Date.now() + 10000;
    while (!existsSync(join(storeDir, "finish"))) {
      if (Date.now() > deadline) throw new Error("délai de libération dépassé");
      await Bun.sleep(5);
    }
    await handle.close();
  }
  `
      );
      const first = Bun.spawn([process.execPath, worker, "A"], {
        stdout: "pipe",
        stderr: "pipe",
      });
      const second = Bun.spawn([process.execPath, worker, "B"], {
        stdout: "pipe",
        stderr: "pipe",
      });
      const waitFor = async (condition: () => boolean): Promise<void> => {
        const deadline = Date.now() + 5000;
        while (!condition()) {
          if (Date.now() > deadline) throw new Error("délai de coordination dépassé");
          await Bun.sleep(5);
        }
      };
      try {
        await waitFor(() => existsSync(join(directory, "ready-A")) || existsSync(join(directory, "ready-B")));
        const winner = existsSync(join(directory, "ready-A")) ? "A" : "B";
        const loser = winner === "A" ? "B" : "A";
        await waitFor(() => existsSync(join(directory, `ready-${loser}`)) || existsSync(join(directory, `result-${loser}`)));
        await writeFile(join(directory, `go-${winner}`), "");
        await waitFor(() => existsSync(join(directory, `result-${winner}`)));
        expect(await readFile(join(directory, `result-${winner}`), "utf8")).toBe("WON");
        await writeFile(join(directory, `go-${loser}`), "");
        await waitFor(() => existsSync(join(directory, `result-${loser}`)));
        expect(await readFile(join(directory, `result-${loser}`), "utf8")).toContain("LOST: verrou");
        expect((await useStore(directory).units.list()).length).toBe(1);
      } finally {
        await writeFile(join(directory, "go-A"), "");
        await writeFile(join(directory, "go-B"), "");
        await writeFile(join(directory, "finish"), "");
        await Promise.all([first.exited, second.exited]);
      }
    }, 20000);
  }

  it("un ancien détenteur ne libère pas le verrou de son remplaçant dans le même processus", async () => {
    const { directory, store } = await initializedStore();
    const replacement = useStore(directory, { force: true });
    await replacement.units.add({ id: "remplacement", track: "build" });
    await store.close();
    const contender = useStore(directory);
    await expect(contender.units.add({ id: "concurrent", track: "build" })).rejects.toThrow("verrou");
    await replacement.close();
    await expect(contender.units.add({ id: "après-libération", track: "build" })).resolves.toMatchObject({ id: "après-libération" });
  });

  it("remplace un verrou périmé dont le pid détenteur est mort", async () => {
    const { directory, store } = await initializedStore();
    await store.close();
    const exited = Bun.spawn(["true"]);
    await exited.exited;
    await writeFile(join(directory, ".orch.lock"), `${exited.pid}\n`);

    const stale: string[] = [];
    const recovered = useStore(directory, {
      onStaleLock: (holder) => stale.push(holder),
    });
    expect(
      await recovered.units.add({ id: "u1", track: "build" })
    ).toMatchObject({ id: "u1" });
    expect(stale).toEqual([String(exited.pid)]);
    await recovered.close();
    expect(await readdir(directory)).not.toContain(".orch.lock");
  });

  it("reprend une migration abandonnée sans laisser de verrou temporaire", async () => {
    const { directory, store } = await initializedStore();
    await store.close();
    const exited = Bun.spawn(["true"]);
    await exited.exited;
    await writeFile(join(directory, ".orch.lock"), `${exited.pid}\n`);
    const migration = join(directory, ".orch.lock.migration");
    await mkdir(migration);
    await writeFile(join(migration, `owner.${exited.pid}.${randomUUID()}`), "");
    const recovered = useStore(directory);
    await expect(recovered.units.add({ id: "récupérée", track: "build" })).resolves.toMatchObject({ id: "récupérée" });
    await recovered.close();
    expect((await readdir(directory)).filter((name) => name.startsWith(".orch.lock"))).toEqual([]);
  });

  it("ne force pas une migration encore active", async () => {
    const { directory, store } = await initializedStore();
    await store.close();
    await writeFile(join(directory, ".orch.lock"), `${process.pid}\n`);
    const migration = join(directory, ".orch.lock.migration");
    await mkdir(migration);
    const marker = `owner.${process.pid}.${randomUUID()}`;
    await writeFile(join(migration, marker), "");
    const contender = useStore(directory, { force: true });
    await expect(contender.units.add({ id: "refusée", track: "build" })).rejects.toThrow("verrou");
    expect(await readFile(join(directory, ".orch.lock"), "utf8")).toBe(`${process.pid}\n`);
    expect(await readdir(migration)).toEqual([marker]);
    expect((await readdir(directory)).filter((name) => name.includes(".tmp."))).toEqual([]);
  });

  it("récupère un répertoire de verrou vide après interruption", async () => {
    const { directory, store } = await initializedStore();
    await store.close();
    await mkdir(join(directory, ".orch.lock"));
    const recovered = useStore(directory);
    await recovered.units.add({ id: "récupérée", track: "build" });
    const markers = await readdir(join(directory, ".orch.lock"));
    expect(markers).toHaveLength(1);
    expect(markers[0]).toMatch(new RegExp(`^owner\\.${process.pid}\\.`));
    await recovered.close();
    expect((await readdir(directory)).filter((name) => name.startsWith(".orch.lock"))).toEqual([]);
  });

  it("préserve les verrous mal formés et refuse les liens symboliques même avec force", async () => {
    const { directory, store } = await initializedStore();
    await store.close();
    const lock = join(directory, ".orch.lock");
    await mkdir(lock);
    await writeFile(join(lock, "note.txt"), "à conserver");
    await expect(useStore(directory, { force: true }).units.add({ id: "refusée", track: "build" })).rejects.toThrow("verrou de magasin invalide");
    expect(await readFile(join(lock, "note.txt"), "utf8")).toBe("à conserver");
    await rm(lock, { recursive: true });
    const outside = await makeDirectory();
    const marker = `owner.${process.pid}.${randomUUID()}`;
    await writeFile(join(outside, marker), "à conserver");
    await symlink(outside, lock);
    await expect(useStore(directory, { force: true }).units.add({ id: "refusée", track: "build" })).rejects.toThrow("lien symbolique interdit");
    expect(await readFile(join(outside, marker), "utf8")).toBe("à conserver");
  });

  it("bloque un rédacteur et ne vole le verrou pid qu’avec force", async () => {
    const { directory, store } = await initializedStore();
    await store.close();
    await writeFile(join(directory, ".orch.lock"), `${process.pid}\n`);

    const blocked = useStore(directory);
    await expect(
      blocked.units.add({ id: "u1", track: "build" })
    ).rejects.toThrow(`verrou de magasin detenu par le pid ${process.pid}`);

    const stolen: string[] = [];
    const forced = useStore(directory, {
      force: true,
      onLockStolen: (holder) => stolen.push(holder),
    });
    expect(
      await forced.units.add({ id: "u1", track: "build" })
    ).toMatchObject({ id: "u1" });
    expect(stolen).toEqual([String(process.pid)]);
    await forced.close();
    expect(await readdir(directory)).not.toContain(".orch.lock");
  });

  it("met les barrières en attente, stocke les consignes permanentes et rend le statut", async () => {
    const { directory, store } = await initializedStore();
    await store.units.add({ id: "u1", track: "build" });
    expect(
      await store.gates.park({
        id: "release",
        question: "Livrer maintenant?",
        options: "ship,wait",
        defaultAnswer: "wait",
      })
    ).toMatchObject({ kind: "open", id: "release" });
    expect(
      await store.standing.add({ line: "Ne jamais force-push." })
    ).toEqual({ number: 1, line: "Ne jamais force-push." });

    const first = await store.status.render();
    expect(first.changed).toBe("premier rendu");
    expect(first.summary.openGateIds).toEqual(["release"]);
    expect(await readFile(join(directory, "status.md"), "utf8")).toContain(
      "| release | open | Livrer maintenant? |"
    );
    expect((await store.status.render()).changed).toBe("aucun changement derive");

    expect(
      await store.gates.resolve({ id: "release", answer: "ship" })
    ).toMatchObject({ kind: "resolved", answer: "ship" });
    expect((await store.status.render()).changed).toBe("barrières ouvertes 1->0");
    expect(await store.gates.list()).toEqual([]);
    expect(await store.standing.show()).toEqual([
      { number: 1, line: "Ne jamais force-push." },
    ]);
  });

  it("résout la frontière GitHub ordonnée et valide un pin facultatif", async () => {
    const { directory, store } = await initializedStore();
    const stack = await makeGitStack(directory);
    const output = JSON.stringify([
      {
        number: 11,
        state: "OPEN",
        headRefName: "stack/open",
        baseRefName: "stack/closed",
        headRefOid: stack.openSha,
      },
      {
        number: 10,
        state: "MERGED",
        headRefName: "stack/merged",
        baseRefName: "main",
        headRefOid: stack.mergedSha,
      },
      {
        number: 13,
        state: "CLOSED",
        headRefName: "stack/closed",
        baseRefName: "stack/merged",
        headRefOid: stack.closedSha,
      },
    ]);

    await withFakeGh({
      directory,
      output,
      operation: async () => {
        expect(await store.frontier.set({ repo: stack.repo })).toEqual({
          generation: 1,
          prs: [
            {
              pr: 10,
              branches: "stack/merged",
              sha: stack.mergedSha,
              state: "MERGED",
            },
            {
              pr: 13,
              branches: "stack/closed",
              sha: stack.closedSha,
              state: "CLOSED",
            },
            {
              pr: 11,
              branches: "stack/open",
              sha: stack.openSha,
              state: "OPEN",
            },
          ],
          lowestUnmerged: 11,
        });
        expect(
          (
            await store.frontier.set({
              repo: stack.repo,
              prs: [10, 13, 11],
            })
          ).generation
        ).toBe(2);
        expect((await store.frontier.show()).generation).toBe(2);
        await expect(
          store.frontier.set({
            repo: stack.repo,
            prs: [10, 11, 12],
          })
        ).rejects.toThrow(
          "l'ancrage de frontiere ne correspond pas: manquantes dans GitHub: 12; en trop dans GitHub: 13"
        );
        await expect(
          store.frontier.set({
            repo: stack.repo,
            prs: [13, 10, 11],
          })
        ).rejects.toThrow(
          "l'ancrage de frontiere ne correspond pas: ordre différent: attendu 13,10,11; GitHub 10,13,11"
        );
        await expect(
          store.frontier.set({
            repo: stack.repo,
            prs: [10, 10],
          })
        ).rejects.toThrow("--prs ne doit pas contenir de doublons");
      },
    });
  });

  it("rejette les piles GitHub ambiguës, cycliques et incomplètes", async () => {
    const { directory, store } = await initializedStore();
    const stack = await makeGitStack(directory);
    const row = (
      number: number,
      state: string,
      headRefName: string,
      baseRefName: string,
      headRefOid: string
    ) => ({ number, state, headRefName, baseRefName, headRefOid });

    await withFakeGh({
      directory,
      output: "[]",
      operation: async (outputPath) => {
        const base = [
          row(10, "MERGED", "stack/merged", "main", stack.mergedSha),
          row(13, "CLOSED", "stack/closed", "stack/merged", stack.closedSha),
          row(11, "OPEN", "stack/open", "stack/closed", stack.openSha),
        ];

        await writeFile(
          outputPath,
          JSON.stringify(
            Array.from({ length: 1000 }, (_, index) =>
              row(
                index + 1,
                "CLOSED",
                `history/${index}`,
                "main",
                stack.openSha
              )
            )
          )
        );
        await expect(
          store.frontier.set({ repo: stack.repo })
        ).rejects.toThrow(
          "gh pr list a renvoyé 1000 PR; l’historique de pile peut être incomplet"
        );

        await writeFile(
          outputPath,
          JSON.stringify([
            ...base,
            row(12, "CLOSED", "stack/open", "main", stack.openSha),
          ])
        );
        expect(await store.frontier.set({ repo: stack.repo })).toMatchObject({
          lowestUnmerged: 11,
        });

        await writeFile(
          outputPath,
          JSON.stringify([
            ...base,
            row(12, "OPEN", "stack/open", "main", stack.openSha),
          ])
        );
        await expect(
          store.frontier.set({ repo: stack.repo })
        ).rejects.toThrow(
          "GitHub a renvoye plusieurs PR pour la branche de tete stack/open: 11,12"
        );

        await writeFile(
          outputPath,
          JSON.stringify([
            ...base,
            row(14, "OPEN", "stack/upstack-a", "stack/open", stack.openSha),
            row(15, "OPEN", "stack/upstack-b", "stack/open", stack.openSha),
          ])
        );
        await expect(
          store.frontier.set({ repo: stack.repo })
        ).rejects.toThrow("la pile de PR GitHub bifurque à stack/open: 14,15");

        await writeFile(
          outputPath,
          JSON.stringify([
            row(10, "MERGED", "stack/merged", "stack/open", stack.mergedSha),
            row(13, "CLOSED", "stack/closed", "stack/merged", stack.closedSha),
            row(11, "OPEN", "stack/open", "stack/closed", stack.openSha),
          ])
        );
        await expect(
          store.frontier.set({ repo: stack.repo })
        ).rejects.toThrow("la pile de PR GitHub contient un cycle a stack/open");

        await writeFile(
          outputPath,
          JSON.stringify([
            row(11, "OPEN", "stack/open", "stack/missing", stack.openSha),
          ])
        );
        await expect(
          store.frontier.set({ repo: stack.repo })
        ).rejects.toThrow(
          "la pile GitHub n'a pas de PR pour la branche de base stack/missing"
        );

        await writeFile(
          outputPath,
          JSON.stringify([
            ...base,
            row(14, "OPEN", "stack/upstack", "stack/open", stack.openSha),
          ])
        );
        await expect(
          store.frontier.set({ repo: stack.repo })
        ).rejects.toThrow("la branche de pile GitHub stack/upstack manque localement");

        await writeFile(
          outputPath,
          JSON.stringify([
            base[0],
            base[1],
            { ...base[2], headRefOid: stack.closedSha },
          ])
        );
        await expect(
          store.frontier.set({ repo: stack.repo })
        ).rejects.toThrow(
          `SHA de tete non concordant pour la PR #11 sur la branche stack/open: GitHub ${stack.closedSha}; local ${stack.openSha}`
        );
      },
    });
  });

  it("conserve un worktree quand sa sonde d’état sale échoue", async () => {
    const directory = await makeDirectory();
    const stack = await makeGitStack(directory);
    const worktree = join(directory, "audit worktree");
    git({
      repo: stack.repo,
      args: ["worktree", "add", "-b", "audit-probe", worktree, "main"],
    });

    const realGit = Bun.which("git");
    if (realGit === null) throw new Error("git est indisponible");
    const bin = join(directory, "audit-bin");
    await mkdir(bin);
    await writeFile(
      join(bin, "git"),
      `#!/usr/bin/env bash
if [ "$1" = "-C" ] && [ "$2" = "$FAIL_STATUS_PATH" ] && [ "$3" = "status" ]; then
  exit 2
fi
exec "$REAL_GIT" "$@"
`
    );
    await writeFile(join(bin, "gh"), "#!/usr/bin/env bash\nprintf '[]\\n'\n");
    await chmod(join(bin, "git"), 0o755);
    await chmod(join(bin, "gh"), 0o755);

    const listed = realpathSync(worktree);
    const result = Bun.spawnSync([WORKTREE_AUDIT, stack.repo], {
      env: {
        ...process.env,
        PATH: `${bin}:${process.env.PATH ?? ""}`,
        REAL_GIT: realGit,
        FAIL_STATUS_PATH: listed,
      },
    });
    expect(result.exitCode).toBe(0);
    const row = result.stdout
      .toString()
      .split("\n")
      .find(
        (line) => line.endsWith(`\t${listed}`) || line.endsWith(`\t${worktree}`)
      );
    expect(row).toBeDefined();
    expect(row?.split("\t")[3]).toBe("unknown");
    expect(row?.split("\t")[7]).toBe("hold-unknown");
  });

  it("s’analyse avec bash -n", () => {
    const syntax = Bun.spawnSync(["bash", "-n", WORKTREE_AUDIT]);
    expect(syntax.exitCode).toBe(0);
    expect(syntax.stderr.toString()).toBe("");
  });

  it("rejette les données TSV, verdict, frontière et inbox mal formés", async () => {
    const { directory, store } = await initializedStore();

    await writeFile(join(directory, "units.tsv"), "wrong\n");
    await expect(store.units.list()).rejects.toThrow(
      "units.tsv a un en-tete invalide"
    );
    await writeFile(
      join(directory, "units.tsv"),
      "id\ttrack\tstate\tbranch\tpr\tsha\tbrief\nshort\trow\n"
    );
    await expect(store.units.list()).rejects.toThrow(
      "units.tsv contient une ligne mal formee"
    );

    await writeFile(
      join(directory, "ledger.tsv"),
      "pr\tsha\tverdict\tevidence\tverifier\tts\n1\tsha\tinvalid\treport\tme\tnow\n"
    );
    await expect(store.ledger.summary()).rejects.toThrow(
      "ledger.tsv contient le verdict invalide invalid"
    );

    await writeFile(join(directory, "frontier.json"), '{"generation":"1"}\n');
    await expect(store.frontier.show()).rejects.toThrow(
      "frontier.json a une forme invalide"
    );

    await writeFile(join(directory, "inbox", "bad.tsv"), "too\tshort\n");
    await expect(store.inbox.peek()).rejects.toThrow(
      "le pointeur de boite de reception bad.tsv est mal forme"
    );
  });

  it("rejette les opérations après fermeture", async () => {
    const { store } = await initializedStore();
    await store.close();
    await expect(store.units.list()).rejects.toThrow("le magasin est ferme");
    await expect(store.status.render()).rejects.toBeInstanceOf(UserError);
  });
});

describe("CLI orch", () => {
  it("affiche l’aide de commande et rejette l’analyse invalide avec le code 1", async () => {
    const help = runCli(["--help"]);
    expect(help.code).toBe(0);
    expect(help.stdout).toContain("Commands:");
    expect(help.stdout).toContain("unit");
    expect(help.stdout).toContain("ledger");

    const frontierHelp = runCli(["frontier", "set", "--help"]);
    expect(frontierHelp.code).toBe(0);
    expect(frontierHelp.stdout).toContain("--repo <dir>");
    expect(frontierHelp.stdout).toContain("--prs <n,...>");

    const directory = await makeDirectory();
    const invalid = runCli(["--store", directory, "unit", "add", "u1"]);
    expect(invalid.code).toBe(1);
    expect(invalid.stderr).toContain("required option '--track <track>'");
  });

  it("accepte ORCH_STORE et émet du JSON complet", async () => {
    const directory = await makeDirectory();
    const env = { ...process.env, ORCH_STORE: directory };
    expect(runCli(["init"], env).code).toBe(0);

    const added = runCli(
      ["unit", "add", "u1", "--track", "build", "--json"],
      env
    );
    expect(added.code).toBe(0);
    expect(JSON.parse(added.stdout)).toEqual({
      id: "u1",
      track: "build",
      state: "pending",
      branch: "",
      pr: "",
      sha: "",
      brief: "",
    });
  });

  it("mappe les résultats utilisateur et introuvables vers les codes de sortie préservés", async () => {
    const directory = await makeDirectory();
    expect(runCli(["--store", directory, "init"]).code).toBe(0);

    const missingRepo = runCli([
      "--store",
      directory,
      "frontier",
      "set",
    ]);
    expect(missingRepo.code).toBe(1);
    expect(missingRepo.stderr).toContain(
      "définir --repo <dir> ou ORCH_REPO"
    );

    const userError = runCli([
      "--store",
      directory,
      "unit",
      "add",
      "",
      "--track",
      "build",
    ]);
    expect(userError.code).toBe(1);
    expect(userError.stderr).toContain("unit id ne doit pas être vide");

    const missingUnit = runCli([
      "--store",
      directory,
      "unit",
      "get",
      "missing",
    ]);
    expect(missingUnit.code).toBe(2);
    expect(missingUnit.stderr).toContain("unité missing introuvable");

    const missingLedger = runCli([
      "--store",
      directory,
      "--json",
      "ledger",
      "check",
      "184530",
      "abc123",
    ]);
    expect(missingLedger.code).toBe(2);
    expect(JSON.parse(missingLedger.stdout)).toEqual({
      pr: "184530",
      sha: "abc123",
      verdict: "NOT-VERIFIED",
    });
    expect(missingLedger.stderr).toBe("");
  });
});
