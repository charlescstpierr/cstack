#!/usr/bin/env python3
"""Compare two model helpers on the same complete T3 preview workload."""

import argparse
import cProfile
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pstats
import statistics
import subprocess
import sys
import tempfile
import time


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependencies(path):
    return {name: digest(path.with_name(name)) for name in ("t3_catalog.py", "project.py")
            if path.with_name(name).is_file()}


def workload(count, schema="v2"):
    now = datetime.now(timezone.utc)
    values = ["level-" + str(index) for index in range(count)]
    if schema == "v1":
        context = {"environmentId": "synthetic-benchmark", "sessionId": "synthetic-benchmark",
                   "capabilitiesSha256": "a" * 64, "traceSha256": "b" * 64, "revalidated": True}
        catalog = {key: value for key, value in context.items() if key != "revalidated"}
        catalog.update(host="t3", observedAt=(now - timedelta(minutes=1)).isoformat(),
                       expiresAt=(now + timedelta(hours=1)).isoformat(),
                       providers={"fixture-provider": {"available": True, "modelsComplete": True,
                           "models": {"fixture-model": {"options": {"effort": {
                               "type": "string", "values": values, "secret": False}}}}}},
                       inheritance={"inheritedProviderInstanceId": "fixture-provider",
                                    "inheritedModel": "fixture-model", "inheritedOptions": {"effort": values[0]}})
        catalog["sha256"] = hashlib.sha256(json.dumps(catalog, sort_keys=True, separators=(",", ":"),
                                                    ensure_ascii=False).encode()).hexdigest()
    elif schema == "v2":
        scope = dict(threadId="synthetic-thread", projectId="synthetic-project", link="synthetic-link",
                     providerInstanceId="fixture-provider", model="fixture-model", runtimeMode="full-access",
                     interactionMode="default", options={"effort": values[0]})
        sources = {name: dict(sha256=letter * 64, itemId=name, toolName=tool,
                             observedAt=(now - timedelta(minutes=1)).isoformat())
                   for name, letter, tool in (("capabilities", "a", "t3-code.orchestrator_capabilities"),
                                              ("thread", "b", "t3-code.t3_thread_read"))}
        catalog = dict(schema="cstack.t3-snapshot/2", host="t3", coordinator=scope, sources=sources,
                       providers={"fixture-provider": dict(enabled=True, canRunChildTask=True,
                           canRunCrossProviderChildTask=True, constraints=[], modelsComplete=True,
                           models={"fixture-model": {"options": {"effort": {"type": "string", "values": values}}}})})
        catalog["sha256"] = hashlib.sha256(json.dumps(catalog, sort_keys=True, separators=(",", ":"),
                                                    ensure_ascii=False).encode()).hexdigest()
        context = dict(schema="cstack.t3-context/2", expectedCoordinator=scope,
                       snapshotSha256=catalog["sha256"], capabilitiesSha256="a" * 64, threadSha256="b" * 64,
                       revalidated=True, revalidatedAt=now.isoformat(), expiresAt=(now + timedelta(hours=1)).isoformat())
    else:
        raise ValueError("unknown benchmark format")
    return catalog, context, values


def preview(module, catalog, context):
    return module.preview({}, "synthetic-config", catalog, host="t3", context=context)


def check(result, values):
    if result.get("unavailable"):
        raise ValueError("preview unavailable: " + json.dumps(result["unavailable"], ensure_ascii=False))
    if result["preflight"]["status"] != "ready":
        raise ValueError("preflight blocked: " + json.dumps(result["preflight"]["errors"], ensure_ascii=False))
    actual = result["supported"]["fixture-provider"]["fixture-model"]["effort"]["values"]
    if actual != values:
        raise ValueError("preview did not validate and return the complete workload")
    return hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("v1", "v2"), default="v2", help="V1 is only for frozen historical helpers")
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--values", type=int, default=2000)
    parser.add_argument("--repetitions", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.values <= 8000 or not 5 <= args.repetitions <= 20:
        parser.error("values must be 1..8000 and repetitions 5..20")
    paths = {"before": args.before.resolve(), "after": args.after.resolve()}
    sources = {name: digest(path) for name, path in paths.items()}
    dependency_sources = {name: dependencies(path) for name, path in paths.items()}
    modules = {name: load(path, "catalog_bench_" + name) for name, path in paths.items()}
    catalog, context, values = workload(args.values, args.format)
    warmed = {}
    for name, module in modules.items():
        try:
            warmed[name] = check(preview(module, catalog, context), values)
        except (KeyError, ValueError, TypeError) as error:
            parser.error(f"BLOCKED: --{name} incompatible avec --format {args.format}: {error}")
    expected = warmed["before"]
    profiler = cProfile.Profile()
    profiler.runcall(preview, modules["before"], catalog, context)
    stats = pstats.Stats(profiler)
    hotspots = [{"function": key[2], "file": Path(key[0]).name, "line": key[1], "own_seconds": row[2]}
                for key, row in sorted(stats.stats.items(), key=lambda item: item[1][2], reverse=True)[:8]]
    rows = []
    for repetition in range(args.repetitions):
        order = ("before", "after") if repetition % 2 == 0 else ("after", "before")
        for name in order:
            started = time.perf_counter()
            try:
                result = preview(modules[name], catalog, context)
                seconds = time.perf_counter() - started
                output_hash = check(result, values)
                if output_hash != expected:
                    raise ValueError("observable output differs between variants")
                rows.append({"variant": name, "repetition": repetition + 1, "seconds": seconds,
                             "error": None, "values_returned": len(values), "output_sha256": output_hash})
            except Exception as error:
                rows.append({"variant": name, "repetition": repetition + 1,
                             "seconds": time.perf_counter() - started, "error": str(error), "values_returned": 0})
    errors = sum(row["error"] is not None for row in rows)
    cli_rows = []
    with tempfile.TemporaryDirectory(prefix="cstack-catalog-cli-") as directory:
        root = Path(directory)
        catalog_path, context_path = root / "catalog.json", root / "context.json"
        catalog_path.write_text(json.dumps(catalog))
        context_path.write_text(json.dumps(context))
        cli_expected = None
        for repetition in range(args.repetitions):
            order = ("before", "after") if repetition % 2 == 0 else ("after", "before")
            for name in order:
                started = time.perf_counter()
                try:
                    result = subprocess.run([sys.executable, str(paths[name]), "--workspace", str(root),
                                             "--host", "t3", "--catalog", str(catalog_path),
                                             "--host-context", str(context_path), "show"],
                                            capture_output=True, text=True, timeout=30, check=True,
                                            env={**os.environ, "XDG_CONFIG_HOME": str(root)})
                    seconds = time.perf_counter() - started
                    output_hash = check(json.loads(result.stdout), values)
                    if cli_expected is None:
                        cli_expected = output_hash
                    if output_hash != cli_expected:
                        raise ValueError("CLI output differs between variants")
                    cli_rows.append({"variant": name, "repetition": repetition + 1, "seconds": seconds,
                                     "error": None, "values_returned": len(values), "output_sha256": output_hash})
                except Exception as error:
                    cli_rows.append({"variant": name, "repetition": repetition + 1,
                                     "seconds": time.perf_counter() - started, "error": str(error), "values_returned": 0})
    errors += sum(row["error"] is not None for row in cli_rows)
    unchanged = (sources == {name: digest(path) for name, path in paths.items()}
                 and dependency_sources == {name: dependencies(path) for name, path in paths.items()})
    summaries = {}
    for phase, results in (("preview", rows), ("cli_show", cli_rows)):
        summary = {}
        for name in paths:
            samples = [row["seconds"] for row in results if row["variant"] == name and row["error"] is None]
            summary[name] = {"samples": len(samples), "median_seconds": statistics.median(samples) if samples else None,
                             "range_seconds": [min(samples), max(samples)] if samples else None}
        summaries[phase] = summary
    payload = {"kind": "synthetic-local-preview", "format": args.format, "python": sys.version, "cpus": os.cpu_count(),
               "load_average": os.getloadavg(), "catalog_bytes": len(json.dumps(catalog).encode()),
               "source_sha256": sources, "dependency_sha256": dependency_sources, "sources_unchanged": unchanged, "errors": errors,
               "complete_previews": sum(row["values_returned"] == len(values) for row in rows + cli_rows),
               "values_per_preview": len(values), "unreported_profile_hotspots": hotspots,
               "summary": summaries, "runs": rows, "cli_runs": cli_rows,
               "verdict": "comparable" if errors == 0 and unchanged else "inconclusive"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(args.output), "verdict": payload["verdict"],
                      "errors": errors, "complete_previews": payload["complete_previews"]}))
    return 0 if payload["verdict"] == "comparable" else 1


if __name__ == "__main__":
    raise SystemExit(main())
