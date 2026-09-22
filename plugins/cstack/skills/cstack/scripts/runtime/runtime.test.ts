import { afterEach, describe, expect, it } from "bun:test";
import { chmod, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
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
  await rm(touched, { force: true });
});

describe("runtime helper", () => {
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
      await fake(h.bin, "cursor-agent", `
if [[ "$1" == "--version" ]]; then echo "cursor fake"; exit 0; fi
if [[ "$1" == "--help" ]]; then echo "--print --output-format --mode --sandbox --workspace --model --force --yolo"; exit 0; fi
printf '%s\\n' "$@" > "$CSTACK_RUNTIME_ARG_CAPTURE"
printf '{"status":"PASS","summary":"cursor ok","checks":[],"findings":[]}'
`);
      const code = await run(["run", "--request", await request(h, "cursor-agent")], h);
      const args = await readFile(capture, "utf8");
      expect(code).toBe(0);
      expect(parsedStdout(h)).toMatchObject({
        provider_requested: "cursor",
        execution: { status: "COMPLETED" },
      });
      expect(args).toContain("--mode\nask");
      expect(args).toContain("--sandbox\nenabled");
      expect(args).not.toContain("--force");
      expect(args).not.toContain("--yolo");
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
