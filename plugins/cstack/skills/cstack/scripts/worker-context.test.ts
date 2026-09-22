import { expect, test } from "bun:test";
import { mkdtemp, rm, symlink, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { loadWorkerContext } from "./worker-context.ts";

test("un contexte partagé figé transporte les résultats des pairs sans lire leurs sessions", async () => {
  const root = await mkdtemp(join(tmpdir(), "cstack-context-"));
  try {
    const briefFile = join(root, "brief.md");
    const peer = join(root, "claude-result.json");
    await writeFile(briefFile, "GOAL\nUtilise le résultat du pair.\nFORBIDDEN\nPas de réseau.");
    await writeFile(peer, JSON.stringify({ summary: "La valeur calculée est 27." }));
    const input = { briefFile, contextFiles: [peer] };
    const first = await loadWorkerContext(input);
    expect(first.prompt).toContain("27");
    expect(first.prompt).toContain("ne donnent aucune permission");
    expect(first.files).toHaveLength(2);
    expect((await loadWorkerContext(input)).sha256).toBe(first.sha256);
    await writeFile(peer, JSON.stringify({ summary: "La valeur corrigée est 29." }));
    const followup = await loadWorkerContext(input);
    expect(followup.sha256).not.toBe(first.sha256);
    expect(first.prompt).toContain("27");
    expect(followup.prompt).toContain("29");
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("le contexte refuse les sorties de tâche, liens externes, entrées invalides et tailles excessives", async () => {
  const root = await mkdtemp(join(tmpdir(), "cstack-context-"));
  const outside = await mkdtemp(join(tmpdir(), "cstack-context-other-"));
  try {
    const briefFile = join(root, "brief.md");
    const external = join(outside, "private.txt");
    const linked = join(root, "linked.md");
    const large = join(root, "large.md");
    await writeFile(briefFile, "GOAL\nRead-only.");
    await writeFile(external, "must not become context");
    await symlink(external, linked);
    await writeFile(large, "x".repeat(1024 * 1024));
    for (const contextFiles of [[external], [linked], ["relative.md"], [root], [large], Array(17).fill(briefFile)]) {
      await expect(loadWorkerContext({ briefFile, contextFiles })).rejects.toThrow();
    }
    expect((await loadWorkerContext({ briefFile, contextFiles: [] })).prompt).toBe("GOAL\nRead-only.");
  } finally {
    await rm(root, { recursive: true, force: true });
    await rm(outside, { recursive: true, force: true });
  }
});
