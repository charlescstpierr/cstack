#!/usr/bin/env python3
"""Observe le Goal natif sur une fixture isolée, sans simuler sa continuation."""

import argparse
from collections import deque
import importlib.util
import json
from pathlib import Path
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_behavior", ROOT / "scripts/verify-behavior.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("authorized", "no-consent"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model")
    parser.add_argument("--effort")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        parser.error("le dossier de sortie doit être vide")
    fixture = Path(tempfile.mkdtemp(prefix="cstack-goal-"))
    (output / "fixture-path.txt").write_text(str(fixture) + "\n")
    skill = ROOT / "plugins/cstack/skills/cstack"
    prompt = (
        f"Applique seulement le contrat runtime à {skill}/references/codex-runtime.md. "
        f"Lis aussi {skill}/agents/openai.yaml comme donnée, pas comme mon message. "
        "Tâche locale isolée en deux phases : crée phase1.txt avec une ligne alpha et vérifie-la, "
        "puis phase2.txt avec une ligne beta et vérifie les deux fichiers. "
        "Pas de délégation, Git, PR ni installation. "
    )
    if args.scenario == "authorized":
        prompt += (
            f"Je demande explicitement un Goal natif global selon {skill}/playbooks/autonomous-run.md. "
            "Termine ton premier tour après la vérification de phase1.txt "
            "avec le travail restant explicite et le Goal actif. La continuation native doit "
            "réutiliser le même Goal pour phase2.txt et le terminer après vérification des deux fichiers."
        )
    (output / "prompt.txt").write_text(prompt + "\n")
    server = runner.AppServer(runner.build_command(), fixture, output / "raw.jsonl", output / "stderr.log")
    goals = []
    turns = []
    snapshots = []
    pending = deque()
    try:
        server.request("initialize", {"clientInfo": {"name": "cstack-goal-probe", "version": "1"}}, 30, lambda _: None)
        server.notify("initialized")
        params = {"cwd": str(fixture), "approvalPolicy": "never", "sandbox": "workspace-write",
                  "developerInstructions": runner.NEUTRAL_INSTRUCTIONS}
        if args.model:
            params["model"] = args.model
        thread = server.request("thread/start", params, 30, lambda _: None)["thread"]["id"]
        turn = {"threadId": thread, "input": [{"type": "text", "text": prompt}]}
        if args.effort:
            turn["effort"] = args.effort
        server.request("turn/start", turn, 30, pending.append)
        deadline = time.monotonic() + 300
        while len(turns) < 4:
            event = pending.popleft() if pending else server.read(deadline)
            if event.get("method") != "turn/completed" or event.get("params", {}).get("threadId") != thread:
                continue
            turns.append(event["params"]["turn"])
            snapshots.append({p.name: p.read_text() for p in fixture.glob("*.txt")})
            goal = server.request("thread/goal/get", {"threadId": thread}, 30, pending.append)["goal"]
            goals.append(goal)
            if not goal or goal["status"] != "active":
                break
        files = {p.name: p.read_text() for p in fixture.glob("*.txt")}
        result = {"scenario": args.scenario, "threadId": thread, "goals": goals,
                  "turns": turns, "files_after_turn": snapshots, "files": files, "model_requested": args.model, "effort_requested": args.effort}
        (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        assert all(t["status"] == "completed" for t in turns), "tour natif non terminé"
        assert files == {"phase1.txt": "alpha\n", "phase2.txt": "beta\n"}, files
        if args.scenario == "authorized":
            assert snapshots[0] == {"phase1.txt": "alpha\n"}, "phase 2 exécutée avant la continuation"
            assert [g["status"] if g else None for g in goals] == ["active", "complete"], goals
            assert goals[0]["objective"] == goals[1]["objective"], "objectif remplacé"
            assert goals[0]["createdAt"] == goals[1]["createdAt"], "Goal recréé"
            assert all(g["tokenBudget"] is None for g in goals), "budget non demandé"
        else:
            assert goals == [None], "Goal créé sans consentement"
        print(f"{args.scenario}: PASS ({len(turns)} tours), preuves: {output}")
    finally:
        server.close()


if __name__ == "__main__":
    main()
