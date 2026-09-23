import { afterEach, describe, expect, it } from "bun:test";
import { chmod, mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative } from "node:path";
import { main } from "./runtime.ts";

const originalPath = process.env.PATH;
const touched = join(tmpdir(), "cstack-runtime-shell-injection");

interface Harness {
  readonly root: string;
  readonly bin: string;
  readonly cwd: string;
  readonly brief: string;
  readonly output: string;
  readonly stdout: string[];
  readonly stderr: string[];
}

async function harness(prefix = "cstack-runtime-"): Promise<Harness> {
  const root = await mkdtemp(join(tmpdir(), prefix));
  const bin = join(root, "bin");
  const cwd = join(root, "repo");
  const brief = join(root, "brief.txt");
  await Bun.$`mkdir -p ${bin} ${cwd}`.quiet();
  await writeFile(brief, "GOAL\nReturn a worker report.\n");
  process.env.PATH = `${bin}${process.env.PATH ? `:${process.env.PATH}` : ""}`;
  return {
    root,
    bin,
    cwd,
    brief,
    output: join(root, "out"),
    stdout: [],
    stderr: [],
  };
}

async function fake(bin: string, name: string, body: string): Promise<void> {
  const path = join(bin, name);
  await writeFile(path, `#!/usr/bin/env bash\nset -euo pipefail\n${body}`);
  await chmod(path, 0o755);
}

async function run(args: readonly string[], h: Harness): Promise<number> {
  return await main(args, {
    stdout: (value) => h.stdout.push(value),
    stderr: (value) => h.stderr.push(value),
  });
}

async function request(h: Harness, runtime: "codex-cli" | "claude-code" | "grok" | "cursor-agent", extra: object = {}): Promise<string> {
  const path = join(h.root, `${runtime}-request.json`);
  await writeFile(path, JSON.stringify({
    selection: { runtime },
    brief_file: h.brief,
    cwd: h.cwd,
    output_dir: h.output,
    permissions: "read-only",
    ...extra,
  }));
  return path;
}

function parsedStdout(h: Harness): unknown {
  return JSON.parse(h.stdout.join(""));
}

afterEach(async () => {
  process.env.PATH = originalPath;
  delete process.env.CSTACK_RUNTIME_ARG_CAPTURE;
  delete process.env.CSTACK_BAD_OUTPUT;
  await rm(touched, { force: true });
});

describe("runtime helper", () => {
  it("documente resume_from dans l'aide", async () => {
    const h = await harness();
    try {
      const code = await run(["--help"], h);
      expect(code).toBe(0);
      expect(h.stdout.join("")).toContain("resume_from?");
    } finally {
      await rm(h.root, { recursive: true, force: true });
    }
  });

  it("probe ne lance pas de login et accepte auth inconnue", async () => {
    const h = await harness();
    try {
      process.env.PATH = h.bin;
      const code = await run(["probe", "grok"], h);
      expect(code).toBe(0);
      expect(parsedStdout(h)).toMatchObject({
        runtime: "grok",
        provider_requested: "xai",
        provider_observed: "unknown",
        available: false,
        auth: "unknown",
      });
    } finally {
      await rm(h.root, { recursive: true, force: true });
    }
  });

  it("lance codex via argv, stdin et fichier final schema", async () => {
    const h = await harness();
    try {
      await fake(h.bin, "codex", `
if [[ "$1" == "--version" ]]; then echo "codex fake"; exit 0; fi
if [[ "$1" == "exec" && "$2" == "--help" ]]; then echo "--config --cd --sandbox --json --output-schema --output-last-message --model --ignore-user-config --ignore-rules"; exit 0; fi
last=""
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--output-last-message" ]]; then shift; last="$1"; fi
  shift || true
done
brief=$(cat)
[[ "$brief" == *"GOAL"* ]]
printf '{"event":"done"}\\n'
cat > "$last" <<'JSON'
{"status":"PASS","summary":"ok","checks":[{"command":"none","result":"ok"}],"findings":[]}
JSON
`);
      const code = await run(["run", "--request", await request(h, "codex-cli")], h);
      const result = parsedStdout(h);
      expect(code).toBe(0);
      expect(result).toMatchObject({
        runtime: "codex-cli",
        provider_requested: "openai",
        provider_observed: "unknown",
        execution: { status: "COMPLETED" },
        worker: { status: "PASS", summary: "ok" },
      });
      expect(existsSync(join(h.output, "worker-report.schema.json"))).toBe(true);
      expect(existsSync(join(h.output, "result.json"))).toBe(true);
    } finally {
      await rm(h.root, { recursive: true, force: true });
    }
  });

  it("transmet les références de skills explicites au bundle", async () => {
    const h = await harness();
    const capture = join(h.root, "prompt.txt");
    try {
      await fake(h.bin, "codex", `
if [[ "$1" == "--version" ]]; then echo "codex fake"; exit 0; fi
if [[ "$1" == "exec" && "$2" == "--help" ]]; then echo "--config --cd --sandbox --json --output-schema --output-last-message --model --ignore-user-config"; exit 0; fi
last=""
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--output-last-message" ]]; then shift; last="$1"; fi
  shift || true
done
cat > "${capture}"
cat > "$last" <<'JSON'
{"status":"PASS","summary":"skills ok","checks":[],"findings":[]}
JSON
`);
      const code = await run([
        "run",
        "--request",
        await request(h, "codex-cli", {
          skills: ["why"],
          skill_references: ["why/references/sources/code-archaeology.md"],
        }),
      ], h);
      expect(code).toBe(0);
      const result = parsedStdout(h) as { skills: { references: string[]; files: { path: string }[] } };
      expect(result.skills.references).toEqual(["why/references/sources/code-archaeology.md"]);
      expect(result.skills.files.map((file) => file.path)).toContain("skills/why/references/sources/code-archaeology.md");
      expect(await readFile(capture, "utf8")).toContain("code-archaeology.md");
    } finally {
      await rm(h.root, { recursive: true, force: true });
    }
  });

  it("ne passe pas par un shell avec le brief", async () => {
    const h = await harness();
    try {
      await writeFile(h.brief, `ignore $(touch ${touched})`);
      await fake(h.bin, "grok", `
if [[ "$1" == "--version" ]]; then echo "grok fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "--prompt-file --cwd --output-format --json-schema --sandbox --permission-mode --tools --allow --deny --no-subagents --model --reasoning-effort"; exit 0; fi
printf '{"status":"PASS","summary":"argv ok","checks":[],"findings":[]}'
`);
      const code = await run(["run", "--request", await request(h, "grok")], h);
      expect(code).toBe(0);
      expect(existsSync(touched)).toBe(false);
    } finally {
      await rm(h.root, { recursive: true, force: true });
    }
  });

  it("classe auth manquante sans PASS", async () => {
    const h = await harness();
    try {
      await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "--print --output-format --json-schema --permission-mode --permission-prompts --restricted --safe-mode --strict-mcp-config --mcp-config --add-dir --tools"; exit 0; fi
echo "login required" >&2
exit 1
`);
      const code = await run(["run", "--request", await request(h, "claude-code")], h);
      const result = parsedStdout(h);
      expect(code).toBe(2);
      expect(result).toMatchObject({
        execution: { status: "AUTH_REQUIRED" },
        worker: { status: "BLOCKED" },
      });
    } finally {
      await rm(h.root, { recursive: true, force: true });
    }
  });

  it("rejette une sortie JSON malformée", async () => {
    const h = await harness();
    try {
      await fake(h.bin, "grok", `
if [[ "$1" == "--version" ]]; then echo "grok fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "--prompt-file --cwd --output-format --json-schema --sandbox --permission-mode --tools --allow --deny --no-subagents --model --reasoning-effort"; exit 0; fi
echo '{"status":"PASS","summary":12}'
`);
      const code = await run(["run", "--request", await request(h, "grok")], h);
      expect(code).toBe(2);
      expect(parsedStdout(h)).toMatchObject({
        execution: { status: "INVALID_OUTPUT" },
        worker: { status: "BLOCKED" },
      });
    } finally {
      await rm(h.root, { recursive: true, force: true });
    }
  });

  it("échoue fermé si un flag requis manque", async () => {
    const h = await harness();
    try {
      await fake(h.bin, "grok", `
if [[ "$1" == "--version" ]]; then echo "grok fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "--prompt-file --cwd --output-format --json-schema --model --reasoning-effort"; exit 0; fi
echo should-not-run
`);
      const code = await run(["run", "--request", await request(h, "grok")], h);
      expect(code).toBe(2);
      expect(parsedStdout(h)).toMatchObject({
        execution: { status: "UNSUPPORTED" },
      });
    } finally {
      await rm(h.root, { recursive: true, force: true });
    }
  });

  it("tue le groupe de processus au timeout", async () => {
    const h = await harness();
    const marker = join(h.root, "descendant-ran");
    try {
      await fake(h.bin, "grok", `
if [[ "$1" == "--version" ]]; then echo "grok fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "--prompt-file --cwd --output-format --json-schema --sandbox --permission-mode --tools --allow --deny --no-subagents --model --reasoning-effort"; exit 0; fi
(sleep 0.6; touch "${marker}") &
wait
`);
      const code = await run([
        "run",
        "--request",
        await request(h, "grok", { timeout_ms: 50 }),
      ], h);
      await new Promise((resolve) => setTimeout(resolve, 900));
      expect(code).toBe(2);
      expect(parsedStdout(h)).toMatchObject({
        execution: { status: "TIMEOUT" },
        worker: { status: "BLOCKED" },
      });
      expect(existsSync(marker)).toBe(false);
    } finally {
      await rm(h.root, { recursive: true, force: true });
    }
  });

  it("applique le profil Claude workspace-write sans Bash ni MCP implicite", async () => {
    const h = await harness();
    const capture = join(h.root, "args.txt");
    process.env.CSTACK_RUNTIME_ARG_CAPTURE = capture;
    try {
      await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "--print --output-format --json-schema --permission-mode --permission-prompts --restricted --safe-mode --strict-mcp-config --mcp-config --add-dir --tools --settings --effort --model"; exit 0; fi
printf '%s\\n' "$@" > "$CSTACK_RUNTIME_ARG_CAPTURE"
cat >/dev/null
printf '{"status":"PASS","summary":"ok","checks":[],"findings":[]}'
`);
      const code = await run([
        "run",
        "--request",
        await request(h, "claude-code", {
          permissions: "workspace-write",
          selection: { runtime: "claude-code", model: "sonnet", reasoning_effort: "high" },
        }),
      ], h);
      const args = await readFile(capture, "utf8");
      expect(code).toBe(0);
      expect(args).toContain("--safe-mode");
      expect(args).toContain("--restricted");
      expect(args).toContain("--strict-mcp-config");
      expect(args).toContain("Read,Glob,Grep,Edit,Write");
      expect(args).not.toContain("Bash");
      expect(args).not.toContain("Agent");
    } finally {
      await rm(h.root, { recursive: true, force: true });
    }
  });

  it("lance Cursor seulement en read-only ask sandboxé", async () => {
    const h = await harness();
    const capture = join(h.root, "cursor-args.txt");
    process.env.CSTACK_RUNTIME_ARG_CAPTURE = capture;
    try {
      await writeFile(h.brief, "Discuss --force and --yolo as text, without enabling them.\n");
      await fake(h.bin, "cursor-agent", `
if [[ "$1" == "--version" ]]; then echo "cursor fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "--print --output-format --mode --sandbox --workspace --model --force --yolo"; exit 0; fi
printf '%s\\0' "$@" > "$CSTACK_RUNTIME_ARG_CAPTURE"
printf '{"status":"PASS","summary":"cursor ok","checks":[],"findings":[]}'
`);
      const code = await run(["run", "--request", await request(h, "cursor-agent")], h);
      const args = (await readFile(capture, "utf8")).split("\0").slice(0, -1);
      expect(code).toBe(0);
      expect(parsedStdout(h)).toMatchObject({
        provider_requested: "cursor",
        execution: { status: "COMPLETED" },
      });
      expect(args.slice(0, 7)).toEqual(["--print", "--output-format", "json", "--mode", "ask", "--sandbox", "enabled"]);
      expect(args).not.toContain("--force");
      expect(args).not.toContain("--yolo");
      expect(args.at(-1)).toContain("--force");
    } finally {
      await rm(h.root, { recursive: true, force: true });
    }
  });

  it("refuse Cursor workspace-write sans contrôle d'outils", async () => {
    const h = await harness();
    try {
      await fake(h.bin, "cursor-agent", `
if [[ "$1" == "--version" ]]; then echo "cursor fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "--print --output-format --mode --sandbox --workspace --model"; exit 0; fi
echo should-not-run
`);
      const code = await run([
        "run",
        "--request",
        await request(h, "cursor-agent", { permissions: "workspace-write" }),
      ], h);
      expect(code).toBe(2);
      expect(parsedStdout(h)).toMatchObject({
        execution: { status: "UNSUPPORTED" },
        worker: { status: "BLOCKED" },
      });
    } finally {
      await rm(h.root, { recursive: true, force: true });
    }
  });
});

const report = { status: "PASS", summary: "peer received", checks: [], findings: [] };
const claudeHelp = "--print --output-format --json-schema --permission-mode --permission-prompts --restricted --safe-mode --strict-mcp-config --mcp-config --add-dir --tools --settings --effort --model";
const claudeResumeHelp = `${claudeHelp} --resume`;
const claudeSession = "123e4567-e89b-12d3-a456-426614174000";

it.each([
  ["structured output", { structured_output: report, session_id: "session-public-id" }, "COMPLETED"],
  ["text envelope", { type: "result", result: JSON.stringify(report) }, "COMPLETED"],
  ["error envelope", { is_error: true, structured_output: report }, "INVALID_OUTPUT"],
  ["error subtype", { subtype: "error_max_turns", structured_output: report }, "INVALID_OUTPUT"],
  ["extra report property", { ...report, trusted: true }, "INVALID_OUTPUT"],
  ["extra structured property", { structured_output: { ...report, trusted: true } }, "INVALID_OUTPUT"],
  ["extra check property", { ...report, checks: [{ command: "test", result: "ok", trusted: true }] }, "INVALID_OUTPUT"],
])("normalise Claude : %s", async (_name, payload, status) => {
  const h = await harness();
  try {
    await writeFile(join(h.bin, "response.json"), JSON.stringify(payload));
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeHelp}"; exit 0; fi
cat >/dev/null
cat "$(dirname "$0")/response.json"
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(status === "COMPLETED" ? 0 : 2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status } });
    expect(JSON.parse(await readFile(join(h.output, "result.json"), "utf8"))).toEqual(parsedStdout(h));
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("préserve le handoff BLOCKED documenté après une exécution réussie", async () => {
  const h = await harness();
  try {
    const contract = await readFile(join(import.meta.dir, "../../references/codex-runtime.md"), "utf8");
    const section = contract.split("## Orchestration requise")[1];
    const template = section?.match(/```json\n([\s\S]*?)\n```/)?.[1];
    if (!template) throw new Error("Handoff JSON absent du contrat");
    await writeFile(join(h.bin, "response.json"), template);
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeHelp}"; exit 0; fi
cat >/dev/null
cat "$(dirname "$0")/response.json"
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    expect(parsedStdout(h)).toMatchObject({
      execution: { status: "COMPLETED" },
      worker: { status: "BLOCKED", checks: [] },
    });
    expect(JSON.parse(await readFile(join(h.output, "result.json"), "utf8"))).toEqual(parsedStdout(h));
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("un refus de découverte bloque la génération même si l'aide contient les bons flags", async () => {
  const h = await harness();
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeHelp}"; exit 1; fi
echo unexpected-generation
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "UNSUPPORTED" } });
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("une sortie tronquée ne devient pas PASS et le reçu existant n'est jamais écrasé", async () => {
  const h = await harness();
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeHelp}"; exit 0; fi
cat >/dev/null
head -c 600000 /dev/zero | tr '\\0' 'x'
`);
    const input = await request(h, "claude-code");
    expect(await run(["run", "--request", input], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "INVALID_OUTPUT", stdout_truncated: true } });
    const before = await readFile(join(h.output, "result.json"), "utf8");
    h.stdout.length = 0;
    expect(await run(["run", "--request", input], h)).toBe(2);
    expect(await readFile(join(h.output, "result.json"), "utf8")).toBe(before);
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("l'annulation attend la fin des descendants même quand le leader ferme ses flux", async () => {
  const h = await harness();
  const started = join(h.root, "started");
  const leaked = join(h.root, "leaked-write");
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeHelp}"; exit 0; fi
cat >/dev/null
trap 'exit 0' TERM INT
bash -c 'trap "" TERM INT; exec >/dev/null 2>&1; sleep 0.8; touch "${leaked}"' &
touch "${started}"
wait
`);
    const pending = run(["run", "--request", await request(h, "claude-code", { timeout_ms: 3000 })], h);
    const deadline = Date.now() + 2000;
    while (!existsSync(started) && Date.now() < deadline) await new Promise((done) => setTimeout(done, 10));
    expect(existsSync(started)).toBe(true);
    process.emit("SIGTERM");
    expect(await pending).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "CANCELLED" } });
    await new Promise((done) => setTimeout(done, 400));
    expect(existsSync(leaked)).toBe(false);
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("préserve le français quand un caractère UTF-8 traverse deux chunks", async () => {
  const h = await harness();
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeHelp}"; exit 0; fi
cat >/dev/null
printf '{"status":"PASS","summary":"\\303'
sleep 0.03
printf '\\251","checks":[],"findings":[]}'
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    expect(parsedStdout(h)).toMatchObject({ worker: { summary: "é" } });
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("refuse de placer les reçus sous les outils d'un worker rédacteur", async () => {
  const h = await harness();
  try {
    const code = await run(["run", "--request", await request(h, "claude-code", {
      permissions: "workspace-write", output_dir: join(h.cwd, "receipts"),
    })], h);
    expect(code).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "FAILED", message: "output_dir doit être hors du worktree inscriptible du worker" } });
    expect(existsSync(join(h.cwd, "receipts"))).toBe(false);
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});


it("résout le PATH relatif avant de changer vers le worktree", async () => {
  const h = await harness();
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeHelp}"; exit 0; fi
cat >/dev/null
printf '{"status":"PASS","summary":"relative path","checks":[],"findings":[]}'
`);
    process.env.PATH = `${relative(process.cwd(), h.bin)}:${originalPath ?? ""}`;
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    expect(parsedStdout(h)).toMatchObject({ worker: { summary: "relative path" } });
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("reprend Claude avec --resume et un prompt sans texte de skills", async () => {
  const h = await harness();
  const args = join(h.root, "args.txt");
  const prompt = join(h.root, "prompt.txt");
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
resume=""
printf '%s\\n' "$@" > "${args}"
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--resume" ]]; then shift; resume="$1"; fi
  shift || true
done
cat > "${prompt}"
sid="${claudeSession}"
if [[ -n "$resume" ]]; then sid="$resume"; fi
printf '{"session_id":"%s","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}' "$sid"
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    const previous = join(h.output, "result.json");
    h.stdout.length = 0;
    const nextOutput = join(h.root, "out-2");
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: nextOutput, resume_from: previous })], h)).toBe(0);
    const result = parsedStdout(h);
    expect(result).toMatchObject({
      execution: { status: "COMPLETED", session_id: claudeSession },
      provenance: { mode: "resume", resumed_from: previous, resume_count: 1 },
    });
    expect(await readFile(args, "utf8")).toContain(claudeSession);
    const resumedPrompt = await readFile(prompt, "utf8");
    expect(resumedPrompt).toContain("RESUMED CSTACK TASK");
    expect(resumedPrompt).not.toContain("# cstack");
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("refuse la reprise sur les runtimes non Claude", async () => {
  const h = await harness();
  try {
    await fake(h.bin, "grok", `
if [[ "$1" == "--version" ]]; then echo "grok fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "--prompt-file --cwd --output-format --json-schema --sandbox --permission-mode --tools --allow --deny --no-subagents --model --reasoning-effort"; exit 0; fi
printf '{"status":"PASS","summary":"ok","checks":[],"findings":[]}'
`);
    const receipt = join(h.root, "receipt.json");
    await writeFile(receipt, "{}");
    expect(await run(["run", "--request", await request(h, "grok", { resume_from: receipt })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "UNSUPPORTED" } });
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("refuse une reprise Claude si le contrat change", async () => {
  const h = await harness();
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
cat >/dev/null
printf '{"session_id":"${claudeSession}","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}'
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    const previous = join(h.output, "result.json");
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", {
      output_dir: join(h.root, "out-2"),
      resume_from: previous,
      permissions: "workspace-write",
    })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "RESUME_FAILED" } });
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("refuse une reprise depuis un reçu périmé", async () => {
  const h = await harness();
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
resume=""
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--resume" ]]; then shift; resume="$1"; fi
  shift || true
done
cat >/dev/null
sid="${claudeSession}"
if [[ -n "$resume" ]]; then sid="$resume"; fi
printf '{"session_id":"%s","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}' "$sid"
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    const first = join(h.output, "result.json");
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "out-2"), resume_from: first })], h)).toBe(0);
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "out-3"), resume_from: first })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "RESUME_FAILED" } });
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("bloque deux reprises simultanées de la même session", async () => {
  const h = await harness();
  const started = join(h.root, "started");
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
resume=""
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--resume" ]]; then shift; resume="$1"; fi
  shift || true
done
cat >/dev/null
if [[ -n "$resume" ]]; then touch "${started}"; sleep 0.6; fi
sid="${claudeSession}"
if [[ -n "$resume" ]]; then sid="$resume"; fi
printf '{"session_id":"%s","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}' "$sid"
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    const previous = join(h.output, "result.json");
    h.stdout.length = 0;
    const first = run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "out-2"), resume_from: previous })], h);
    const deadline = Date.now() + 1000;
    while (!existsSync(started) && Date.now() < deadline) await new Promise((done) => setTimeout(done, 10));
    const h2 = { ...h, output: join(h.root, "out-3"), stdout: [], stderr: [] };
    expect(await run(["run", "--request", await request(h2, "claude-code", { resume_from: previous })], h2)).toBe(2);
    expect(JSON.parse(h2.stdout.join(""))).toMatchObject({ execution: { status: "RESUME_FAILED" } });
    expect(await first).toBe(0);
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("rend la lignée non reprenable après timeout de reprise", async () => {
  const h = await harness();
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
resume=""
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--resume" ]]; then shift; resume="$1"; fi
  shift || true
done
cat >/dev/null
if [[ -n "$resume" ]]; then sleep 1; fi
printf '{"session_id":"${claudeSession}","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}'
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    const previous = join(h.output, "result.json");
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "out-2"), resume_from: previous, timeout_ms: 50 })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "TIMEOUT" } });
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "out-3"), resume_from: previous })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "RESUME_FAILED" } });
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it.each([
  ["missing id", '{"status":"PASS","summary":"ok","checks":[],"findings":[]}'],
  ["changed id", '{"session_id":"123e4567-e89b-12d3-a456-426614174999","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}'],
])("refuse une reprise avec session_id %s", async (_name, payload) => {
  const h = await harness();
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
resume=""
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--resume" ]]; then shift; resume="$1"; fi
  shift || true
done
cat >/dev/null
if [[ -n "$resume" ]]; then printf '${payload}'; else printf '{"session_id":"${claudeSession}","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}'; fi
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    const previous = join(h.output, "result.json");
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "out-2"), resume_from: previous })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "RESUME_FAILED" } });
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("classe le message Claude réel de session introuvable comme RESUME_FAILED", async () => {
  const h = await harness();
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
resume=""
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--resume" ]]; then shift; resume="$1"; fi
  shift || true
done
cat >/dev/null
if [[ -n "$resume" ]]; then echo "No conversation found with session ID: $resume" >&2; exit 1; fi
printf '{"session_id":"${claudeSession}","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}'
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    const previous = join(h.output, "result.json");
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "out-2"), resume_from: previous })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "RESUME_FAILED" } });
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("classe une session reprise introuvable sans masquer l'auth réelle", async () => {
  const h = await harness();
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
resume=""
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--resume" ]]; then shift; resume="$1"; fi
  shift || true
done
cat >/dev/null
if [[ -n "$resume" ]]; then echo "session not found" >&2; exit 1; fi
printf '{"session_id":"${claudeSession}","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}'
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    const previous = join(h.output, "result.json");
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "out-2"), resume_from: previous })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "RESUME_FAILED" } });
    h.stdout.length = 0;
    await writeFile(join(h.output, "resume-state.json"), JSON.stringify({ current_result: previous, session_id: claudeSession, status: "IDLE", resume_count: 0 }));
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
cat >/dev/null
echo '{"session_id":"${claudeSession}","error":"authentication failed"}' >&2
exit 1
`);
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "out-3"), resume_from: previous })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "AUTH_REQUIRED" } });
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("refuse les changements de contrat sans génération et garde la tête reprenable", async () => {
  const h = await harness();
  const generationCount = join(h.root, "generations");
  const otherCwd = join(h.root, "other-repo");
  const otherTask = join(h.root, "other-task");
  const otherBrief = join(otherTask, "brief.txt");
  try {
    await Bun.$`mkdir -p ${otherCwd} ${otherTask}`.quiet();
    await writeFile(otherBrief, "GOAL\nOther task.\n");
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "\${CSTACK_FAKE_CLAUDE_VERSION:-claude fake}"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
resume=""
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--resume" ]]; then shift; resume="$1"; fi
  shift || true
done
cat >/dev/null
echo run >> "${generationCount}"
sid="${claudeSession}"
if [[ -n "$resume" ]]; then sid="$resume"; fi
printf '{"session_id":"%s","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}' "$sid"
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    const previous = join(h.output, "result.json");
    const baseRuns = (await readFile(generationCount, "utf8")).trim().split("\n").length;
    const cases = [
      ["cwd", { cwd: otherCwd }],
      ["task", { brief_file: otherBrief }],
      ["selection", { selection: { runtime: "claude-code", model: "opus" } }],
      ["effort", { selection: { runtime: "claude-code", model: "opus", reasoning_effort: "high" } }],
      ["skills", { skills: ["why"] }],
    ] as const;
    for (const [name, extra] of cases) {
      h.stdout.length = 0;
      expect(await run(["run", "--request", await request(h, "claude-code", { ...extra, output_dir: join(h.root, `bad-${name}`), resume_from: previous })], h)).toBe(2);
      expect(parsedStdout(h)).toMatchObject({ execution: { status: "RESUME_FAILED" } });
      expect((await readFile(generationCount, "utf8")).trim().split("\n").length).toBe(baseRuns);
    }
    process.env.CSTACK_FAKE_CLAUDE_VERSION = "claude changed";
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "bad-version"), resume_from: previous })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "RESUME_FAILED" } });
    expect((await readFile(generationCount, "utf8")).trim().split("\n").length).toBe(baseRuns);
    process.env.CSTACK_FAKE_CLAUDE_VERSION = "claude fake";
    const originalReceipt = await readFile(previous, "utf8");
    const receipt = JSON.parse(originalReceipt);
    receipt.provenance.resume_count = 8;
    await writeFile(previous, JSON.stringify(receipt));
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "bad-limit"), resume_from: previous })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "RESUME_FAILED", message: "resume_from: limite de reprises atteinte" } });
    expect((await readFile(generationCount, "utf8")).trim().split("\n").length).toBe(baseRuns);
    await writeFile(previous, originalReceipt);
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "good-resume"), resume_from: previous })], h)).toBe(0);
    expect((await readFile(generationCount, "utf8")).trim().split("\n").length).toBe(baseRuns + 1);
  } finally {
    delete process.env.CSTACK_FAKE_CLAUDE_VERSION;
    await rm(h.root, { recursive: true, force: true });
  }
});

it("refuse reçus et états de reprise non fiables sans empoisonner la tête", async () => {
  const h = await harness();
  const generationCount = join(h.root, "generations");
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
resume=""
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--resume" ]]; then shift; resume="$1"; fi
  shift || true
done
cat >/dev/null
echo run >> "${generationCount}"
sid="${claudeSession}"
if [[ -n "$resume" ]]; then sid="$resume"; fi
printf '{"session_id":"%s","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}' "$sid"
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    const previous = join(h.output, "result.json");
    const state = join(h.output, "resume-state.json");
    const linkedReceipt = join(h.root, "linked-result.json");
    await symlink(previous, linkedReceipt);
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "bad-symlink"), resume_from: linkedReceipt })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "RESUME_FAILED" } });
    const validState = await readFile(state, "utf8");
    await writeFile(state, "{");
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "bad-state"), resume_from: previous })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "RESUME_FAILED" } });
    expect(existsSync(join(h.output, "resume.lock"))).toBe(false);
    await writeFile(state, validState);
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "good-resume-after-bad-state"), resume_from: previous })], h)).toBe(0);
    expect((await readFile(generationCount, "utf8")).trim().split("\n").length).toBe(2);
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("un --help sans --resume ne prend pas le verrou et permet de réessayer", async () => {
  const h = await harness();
  const generationCount = join(h.root, "generations");
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then
  if [[ "\${CSTACK_HELP_WITH_RESUME:-1}" == "1" ]]; then echo "${claudeResumeHelp}"; else echo "${claudeHelp}"; fi
  exit 0
fi
resume=""
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--resume" ]]; then shift; resume="$1"; fi
  shift || true
done
cat >/dev/null
echo run >> "${generationCount}"
sid="${claudeSession}"
if [[ -n "$resume" ]]; then sid="$resume"; fi
printf '{"session_id":"%s","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}' "$sid"
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    const previous = join(h.output, "result.json");
    process.env.CSTACK_HELP_WITH_RESUME = "0";
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "bad-help"), resume_from: previous })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "UNSUPPORTED" } });
    expect(existsSync(join(h.output, "resume.lock"))).toBe(false);
    expect((await readFile(generationCount, "utf8")).trim().split("\n").length).toBe(1);
    process.env.CSTACK_HELP_WITH_RESUME = "1";
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "good-after-help"), resume_from: previous })], h)).toBe(0);
    expect((await readFile(generationCount, "utf8")).trim().split("\n").length).toBe(2);
  } finally {
    delete process.env.CSTACK_HELP_WITH_RESUME;
    await rm(h.root, { recursive: true, force: true });
  }
});

it("garde AUTH_REQUIRED prioritaire sur une erreur de session expirée", async () => {
  const h = await harness();
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
resume=""
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--resume" ]]; then shift; resume="$1"; fi
  shift || true
done
cat >/dev/null
if [[ -n "$resume" ]]; then echo "session expired, please log in" >&2; exit 1; fi
printf '{"session_id":"${claudeSession}","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}'
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    const previous = join(h.output, "result.json");
    h.stdout.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "expired"), resume_from: previous })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "AUTH_REQUIRED" } });
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("classe un reçu resume_from manquant comme RESUME_FAILED", async () => {
  const h = await harness();
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
echo should-not-run
`);
    const missing = join(h.root, "missing", "result.json");
    expect(await run(["run", "--request", await request(h, "claude-code", { resume_from: missing })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "RESUME_FAILED" } });
  } finally {
    await rm(h.root, { recursive: true, force: true });
  }
});

it("libère le verrou si la finalisation du reçu échoue", async () => {
  const h = await harness();
  try {
    await fake(h.bin, "claude", `
if [[ "$1" == "--version" ]]; then echo "claude fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "${claudeResumeHelp}"; exit 0; fi
resume=""
while [[ "$#" -gt 0 ]]; do
  if [[ "$1" == "--resume" ]]; then shift; resume="$1"; fi
  shift || true
done
cat >/dev/null
if [[ -n "$resume" && -n "\${CSTACK_BAD_OUTPUT:-}" ]]; then mkdir -p "$CSTACK_BAD_OUTPUT/result.json"; fi
sid="${claudeSession}"
if [[ -n "$resume" ]]; then sid="$resume"; fi
printf '{"session_id":"%s","structured_output":{"status":"PASS","summary":"ok","checks":[],"findings":[]}}' "$sid"
`);
    expect(await run(["run", "--request", await request(h, "claude-code")], h)).toBe(0);
    const previous = join(h.output, "result.json");
    const badOutput = join(h.root, "io-fails");
    process.env.CSTACK_BAD_OUTPUT = badOutput;
    h.stdout.length = 0;
    h.stderr.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: badOutput, resume_from: previous })], h)).toBe(64);
    expect(h.stderr.join("")).toContain("runtime:");
    expect(existsSync(join(h.output, "resume.lock"))).toBe(false);
    delete process.env.CSTACK_BAD_OUTPUT;
    h.stdout.length = 0;
    h.stderr.length = 0;
    expect(await run(["run", "--request", await request(h, "claude-code", { output_dir: join(h.root, "after-io-fail"), resume_from: previous })], h)).toBe(2);
    expect(parsedStdout(h)).toMatchObject({ execution: { status: "RESUME_FAILED" } });
  } finally {
    delete process.env.CSTACK_BAD_OUTPUT;
    await rm(h.root, { recursive: true, force: true });
  }
});
