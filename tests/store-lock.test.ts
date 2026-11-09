import { expect, test } from "bun:test";
import { mkdtemp, writeFile, readFile, rm, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const modulePath = process.env.CSTACK_LOCK_STORE_MODULE ?? join(import.meta.dir, "../plugins/cstack/skills/cstack/scripts/orch/store.ts");

test("écrivains concurrents : la reprise périmée ne chevauche jamais un successeur", async () => {
  const dir = await mkdtemp(join(tmpdir(), "cstack-lock-race-"));
  const worker = join(dir, "writer.ts");
  const children: Bun.Subprocess<"ignore", "pipe", "pipe">[] = [];
  try {
    await mkdir(join(dir, "store"));
    await writeFile(worker, `
import { existsSync } from "node:fs";
import { join } from "node:path";
const fs = { ...await import("node:fs/promises") };
const dir = ${JSON.stringify(dir)};
const id = process.argv[2];
const wait = async name => { while (!existsSync(join(dir, name))) await Bun.sleep(5); };
const { openStore } = await import(${JSON.stringify(modulePath)});
const store = openStore(join(dir, "store"), { onStaleLock() {
  // Freeze real writers after observing the dead owner, before takeover.
  require("node:fs").writeFileSync(join(dir, "ready-" + id), "");
  const deadline = Date.now() + 8000;
  while (!existsSync(join(dir, "go-" + id))) {
    if (Date.now() > deadline) throw new Error("stale-owner barrier timeout");
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 5);
  }
}});
try {
  if (id === "init") { await store.init(); }
  else {
    try { await store.units.add({ id, track: "build" }); }
    catch (error) {
      if (/verrou|store lock/.test(error.message)) {
        await fs.writeFile(join(dir, "result-" + id), "blocked");
        process.exit(0);
      }
      throw error;
    }
    try { await fs.mkdir(join(dir, "critical")); }
    catch {
      await fs.writeFile(join(dir, "result-" + id), "overlap");
      throw new Error("OVERLAP: two writers own the store");
    }
    await fs.writeFile(join(dir, "result-" + id), "entered");
    await wait("finish");
    await fs.rmdir(join(dir, "critical"));
  }
} finally { await store.close(); }
`);
    const launch = (id: string) => {
      const child = Bun.spawn([process.execPath, worker, id], { stdout: "pipe", stderr: "pipe" });
      children.push(child);
      return child;
    };
    const init = launch("init");
    expect(await init.exited).toBe(0);
    const dead = Bun.spawn(["true"]);
    await dead.exited;
    await writeFile(join(dir, "store", ".orch.lock"), `${dead.pid}\n`);
    for (const id of ["A", "B", "C"]) {
      launch(id);
      const deadline = Date.now() + 8000;
      while (!existsSync(join(dir, "ready-" + id)) && !existsSync(join(dir, "result-" + id))) {
        if (Date.now() > deadline) throw new Error(`writer ${id} did not reach the barrier`);
        await Bun.sleep(5);
      }
    }
    for (const [index, id] of ["A", "B", "C"].entries()) {
      await writeFile(join(dir, "go-" + id), "");
      const deadline = Date.now() + 8000;
      while (!existsSync(join(dir, "result-" + id)) && children[index + 1]?.exitCode === null) {
        if (Date.now() > deadline) throw new Error(`writer ${id} did not finish`);
        await Bun.sleep(5);
      }
    }
    await writeFile(join(dir, "finish"), "");
    const results = await Promise.all(children.map(async child => ({
      code: await child.exited, stderr: await new Response(child.stderr).text(),
    })));
    expect(results).toEqual(results.map(() => ({ code: 0, stderr: "" })));
    const outcomes = await Promise.all(["A", "B", "C"].map(id => readFile(join(dir, "result-" + id), "utf8")));
    expect(outcomes.filter(value => value === "entered")).toHaveLength(1);
  } finally {
    for (const id of ["A", "B", "C"]) await writeFile(join(dir, "go-" + id), "");
    await writeFile(join(dir, "finish"), "");
    for (const child of children) if (child.exitCode === null) child.kill();
    await Promise.all(children.map(child => child.exited));
    await rm(dir, { recursive: true, force: true });
  }
}, 20000);


test("huit écrivains conservent toutes les unités après la mort du propriétaire", async () => {
  const dir = await mkdtemp(join(tmpdir(), "cstack-lock-crash-"));
  const worker = join(dir, "writer.ts");
  const children: Bun.Subprocess<"ignore", "pipe", "pipe">[] = [];
  try {
    await writeFile(worker, `
import { openStore } from ${JSON.stringify(modulePath)};
import { writeFile } from "node:fs/promises";
const dir = ${JSON.stringify(dir)};
const id = process.argv[2];
const store = openStore(dir);
try {
  if (id === "owner") {
    await store.init();
    await writeFile(dir + "/ready", "");
    await Bun.sleep(30000);
  } else {
    const deadline = Date.now() + 8000;
    while (true) {
      try { await store.units.add({ id, track: "build" }); break; }
      catch (error) {
        if (!/verrou|store lock/.test(error.message) || Date.now() > deadline) throw error;
        await Bun.sleep(5);
      }
    }
  }
} finally { await store.close(); }
`);
    const launch = (id: string) => {
      const child = Bun.spawn([process.execPath, worker, id], { stdout: "pipe", stderr: "pipe" });
      children.push(child);
      return child;
    };
    const owner = launch("owner");
    const deadline = Date.now() + 8000;
    while (!existsSync(join(dir, "ready"))) {
      if (Date.now() > deadline) throw new Error("owner did not acquire");
      await Bun.sleep(5);
    }
    owner.kill(9);
    await owner.exited;
    const writers = Array.from({ length: 8 }, (_, index) => launch(String(index)));
    const results = await Promise.all(writers.map(async child => ({
      code: await child.exited, stderr: await new Response(child.stderr).text(),
    })));
    expect(results).toEqual(results.map(() => ({ code: 0, stderr: "" })));
    const rows = (await readFile(join(dir, "units.tsv"), "utf8")).trim().split("\n").slice(1);
    expect(rows).toHaveLength(8);
    expect(new Set(rows.map(row => row.split("\t")[0])).size).toBe(8);
  } finally {
    for (const child of children) if (child.exitCode === null) child.kill(9);
    await Promise.all(children.map(child => child.exited));
    await rm(dir, { recursive: true, force: true });
  }
}, 20000);
