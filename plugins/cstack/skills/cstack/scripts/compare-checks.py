#!/usr/bin/env python3
"""Compare two bounded, passive check-observation reports."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union


MAX_REPORT_BYTES = 1024 * 1024
MAX_RECORDS = 10000
OUTCOMES = frozenset(("pass", "fail", "error", "skip", "not_run"))
FAILURES = frozenset(("fail", "error"))
HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class ReportError(ValueError):
    """Raised when an observation report does not satisfy the input contract."""


def _duplicate_keys(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReportError('clé JSON dupliquée : %r' % key)
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ReportError('constante JSON invalide : %s' % value)


def _parse_json(raw: bytes, source: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ReportError('%s n’est pas en UTF-8 : %s' % (source, error)) from error
    try:
        return json.loads(
            text,
            object_pairs_hook=_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as error:
        raise ReportError('%s n’est pas un JSON valide : %s' % (source, error)) from error
    except RecursionError as error:
        raise ReportError('%s contient trop de niveaux imbriqués' % source) from error


def load_report(path: Union[os.PathLike, str]) -> Dict[str, Any]:
    """Read and validate one report without reading any referenced evidence file."""

    source = os.fspath(path)
    try:
        with open(source, "rb") as handle:
            raw = handle.read(MAX_REPORT_BYTES + 1)
    except OSError as error:
        raise ReportError('lecture impossible de %s : %s' % (source, error)) from error
    if len(raw) > MAX_REPORT_BYTES:
        raise ReportError('%s dépasse la limite de %d octets' % (source, MAX_REPORT_BYTES))
    return validate_report(_parse_json(raw, source), source)


def _require_keys(value: Mapping[str, Any], expected: Sequence[str], where: str) -> None:
    actual = set(value)
    wanted = set(expected)
    unexpected = sorted((repr(key) for key in actual - wanted))
    missing = sorted(wanted - actual)
    if unexpected:
        raise ReportError('%s contient des clés inattendues : %s' % (where, ", ".join(unexpected)))
    if missing:
        raise ReportError('%s manque de clés : %s' % (where, ", ".join(missing)))


def _nonempty_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReportError('%s doit être une chaîne non vide' % where)
    return value


def _hash_or_none(value: Any, where: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or HASH_RE.fullmatch(value) is None:
        raise ReportError('%s doit être null ou un SHA-256 de 64 caractères hexadécimaux' % where)
    return value.lower()


def validate_report(report: Any, source: str = "report") -> Dict[str, Any]:
    """Validate and copy one report at the trust boundary."""

    if not isinstance(report, dict):
        raise ReportError('%s doit être un objet JSON' % source)
    _require_keys(
        report,
        ("version", "revision", "scope", "environment", "inventory_complete", "checks"),
        source,
    )
    if type(report["version"]) is not int or report["version"] != 1:
        raise ReportError('%s.version doit être l’entier 1' % source)
    revision = report["revision"]
    if not isinstance(revision, dict):
        raise ReportError('%s.revision doit être un objet' % source)
    _require_keys(revision, ("commit", "patch_sha256"), "%s.revision" % source)
    commit = revision["commit"]
    if not isinstance(commit, str) or COMMIT_RE.fullmatch(commit) is None:
        raise ReportError('%s.revision.commit doit contenir 40 caractères hexadécimaux' % source)
    patch_sha256 = _hash_or_none(revision["patch_sha256"], "%s.revision.patch_sha256" % source)
    scope = _nonempty_string(report["scope"], "%s.scope" % source)
    environment = _nonempty_string(report["environment"], "%s.environment" % source)
    if type(report["inventory_complete"]) is not bool:
        raise ReportError('%s.inventory_complete doit être un booléen' % source)
    checks = report["checks"]
    if not isinstance(checks, list):
        raise ReportError('%s.checks doit être une liste' % source)
    if len(checks) > MAX_RECORDS:
        raise ReportError('%s.checks dépasse la limite de %d contrôles' % (source, MAX_RECORDS))

    copied_checks: List[Dict[str, Any]] = []
    check_ids = set()
    total_runs = 0
    for index, check in enumerate(checks):
        where = "%s.checks[%d]" % (source, index)
        if not isinstance(check, dict):
            raise ReportError('%s doit être un objet' % where)
        _require_keys(check, ("id", "definition_sha256", "runs"), where)
        check_id = _nonempty_string(check["id"], "%s.id" % where)
        if check_id in check_ids:
            raise ReportError('identifiant de contrôle dupliqué : %s' % check_id)
        check_ids.add(check_id)
        definition_sha256 = _hash_or_none(check["definition_sha256"], "%s.definition_sha256" % where)
        runs = check["runs"]
        if not isinstance(runs, list):
            raise ReportError('%s.runs doit être une liste' % where)
        total_runs += len(runs)
        if total_runs > MAX_RECORDS:
            raise ReportError('le rapport dépasse la limite de %d observations' % MAX_RECORDS)
        copied_runs: List[Dict[str, str]] = []
        for run_index, run in enumerate(runs):
            run_where = "%s.runs[%d]" % (where, run_index)
            if not isinstance(run, dict):
                raise ReportError('%s doit être un objet' % run_where)
            _require_keys(run, ("outcome", "evidence"), run_where)
            outcome = run["outcome"]
            if not isinstance(outcome, str) or outcome not in OUTCOMES:
                raise ReportError('%s.outcome est inconnu' % run_where)
            evidence = run["evidence"]
            if not isinstance(evidence, str):
                raise ReportError('%s.evidence doit être une chaîne' % run_where)
            copied_runs.append({"outcome": outcome, "evidence": evidence})
        copied_checks.append(
            {
                "id": check_id,
                "definition_sha256": definition_sha256,
                "runs": copied_runs,
            }
        )
    return {
        "version": 1,
        "revision": {"commit": commit.lower(), "patch_sha256": patch_sha256},
        "scope": scope,
        "environment": environment,
        "inventory_complete": report["inventory_complete"],
        "checks": copied_checks,
    }


def _observations(runs: Sequence[Mapping[str, str]]) -> Tuple[str, Optional[str], str]:
    if not runs:
        return "incomparable", None, 'aucune observation enregistrée'
    outcomes = {run["outcome"] for run in runs}
    if "skip" in outcomes or "not_run" in outcomes:
        return "incomparable", None, 'un contrôle a été ignoré ou non exécuté'
    if len(outcomes) != 1:
        return "unstable", None, 'les observations répétées ont des résultats différents'
    outcome = next(iter(outcomes))
    if outcome in FAILURES:
        evidence = {run["evidence"] for run in runs}
        if len(evidence) != 1:
            return "unstable", None, 'les observations répétées des échecs diffèrent'
    return "consistent", outcome, ""


def _record(check: Optional[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    if check is None:
        return None
    return {
        "definition_sha256": check["definition_sha256"],
        "runs": [
            {"outcome": run["outcome"], "evidence": run["evidence"]}
            for run in check["runs"]
        ],
    }


def _classify(
    base: Optional[Mapping[str, Any]],
    candidate: Optional[Mapping[str, Any]],
    metadata_reasons: Sequence[str],
) -> Tuple[str, List[str]]:
    reasons: List[str] = []
    if metadata_reasons:
        reasons.extend(metadata_reasons)
    if metadata_reasons:
        reasons.append('les inventaires ne permettent pas une comparaison complète')
        return 'incomparable', _unique(reasons)
    if base is None:
        if candidate is not None and candidate["runs"]:
            label = "added_check"
            reasons.append('ce contrôle apparaît dans l’inventaire candidat')
        else:
            label = "incomparable"
            reasons.append('le contrôle candidat n’a aucune observation')
        return label, _unique(reasons)
    if candidate is None:
        return 'removed_or_unobserved', ['ce contrôle est absent de l’inventaire candidat']

    base_definition = base["definition_sha256"]
    candidate_definition = candidate["definition_sha256"]
    if base_definition is None or candidate_definition is None:
        label = "definition_unknown"
        reasons.append('une empreinte de définition du contrôle manque')
        return label, _unique(reasons)
    if base_definition != candidate_definition:
        label = "definition_changed"
        reasons.append('l’empreinte de définition du contrôle a changé')
        return label, _unique(reasons)

    base_state, base_outcome, base_reason = _observations(base["runs"])
    candidate_state, candidate_outcome, candidate_reason = _observations(candidate["runs"])
    if base_state == "incomparable" or candidate_state == "incomparable":
        label = "incomparable"
        reasons.extend(reason for reason in (base_reason, candidate_reason) if reason)
    elif base_state == "unstable" or candidate_state == "unstable":
        label = "unstable"
        reasons.extend(reason for reason in (base_reason, candidate_reason) if reason)
    elif base_outcome == "pass" and candidate_outcome == "pass":
        if len(base["runs"]) < 2 or len(candidate["runs"]) < 2:
            label = "insufficient_observations"
            reasons.append('au moins deux observations passantes sont nécessaires par côté')
        else:
            label = "no_difference_observed"
            reasons.append('les deux côtés enregistrent des observations passantes cohérentes')
    elif base_outcome == "pass" and candidate_outcome in FAILURES:
        label = "regression"
        reasons.append('un contrôle passant est devenu un échec ou une erreur')
    elif base_outcome in FAILURES and candidate_outcome == "pass" and len(candidate["runs"]) < 2:
        label = "insufficient_observations"
        reasons.append("au moins deux observations passantes du candidat sont nécessaires")
    elif base_outcome in FAILURES and candidate_outcome == "pass":
        label = "fixed_failure"
        reasons.append('l’échec de la base n’est plus observé ; une revue reste nécessaire')
    elif base_outcome in FAILURES and candidate_outcome in FAILURES:
        base_evidence = {run["evidence"] for run in base["runs"]}
        candidate_evidence = {run["evidence"] for run in candidate["runs"]}
        if base_outcome == candidate_outcome and base_evidence == candidate_evidence:
            label = "persistent_failure"
            reasons.append('les mêmes observations d’échec restent présentes ; cela ne prouve pas une cause préexistante')
        else:
            label = "failure_changed"
            reasons.append('le résultat ou l’observation de l’échec a changé')
    else:
        label = "incomparable"
        reasons.append('les observations ne décrivent pas des résultats comparables')
    return label, _unique(reasons)


def _unique(values: Sequence[str]) -> List[str]:
    result: List[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _compare_validated(base_report: Mapping[str, Any], candidate_report: Mapping[str, Any]) -> Dict[str, Any]:
    base_checks = {check["id"]: check for check in base_report["checks"]}
    candidate_checks = {check["id"]: check for check in candidate_report["checks"]}
    metadata_reasons: List[str] = []
    if base_report["scope"] != candidate_report["scope"]:
        metadata_reasons.append('les périmètres des rapports diffèrent')
    if base_report["environment"] != candidate_report["environment"]:
        metadata_reasons.append('les environnements des rapports diffèrent')
    if not base_report["inventory_complete"]:
        metadata_reasons.append('l’inventaire de la base est incomplet')
    if not candidate_report["inventory_complete"]:
        metadata_reasons.append('l’inventaire candidat est incomplet')
    if not base_checks:
        metadata_reasons.append('l’inventaire de la base est vide')
    if not candidate_checks:
        metadata_reasons.append('l’inventaire candidat est vide')
    check_results = []
    for check_id in sorted(set(base_checks) | set(candidate_checks)):
        base_check = base_checks.get(check_id)
        candidate_check = candidate_checks.get(check_id)
        label, row_reasons = _classify(base_check, candidate_check, metadata_reasons)
        check_results.append({
            "id": check_id,
            "label": label,
            "base": _record(base_check),
            "candidate": _record(candidate_check),
            "reasons": row_reasons,
        })
    labels = {check["label"] for check in check_results}
    if metadata_reasons or labels & {
        "incomparable",
        "definition_unknown",
        "removed_or_unobserved",
        "insufficient_observations",
    }:
        status = "incomparable"
    elif "unstable" in labels:
        status = "unstable"
    elif "regression" in labels:
        status = "regression"
    elif labels & {"definition_changed", "failure_changed", "added_check", "fixed_failure"}:
        status = "changes_observed"
    elif "persistent_failure" in labels:
        status = "persistent_failure"
    elif labels == {"no_difference_observed"}:
        status = "no_difference_observed"
    else:
        status = "incomparable"

    reasons = list(metadata_reasons)
    if status == "no_difference_observed":
        reasons.append('tous les contrôles ont des observations passantes cohérentes et comparables')
    elif status == "regression":
        reasons.append('au moins un contrôle passant est devenu un échec ou une erreur')
    elif status == "unstable":
        reasons.append('les observations répétées sont contradictoires')
    elif status == "persistent_failure":
        reasons.append('un échec reste présent des deux côtés ; aucune cause préexistante n’est déduite')
    elif status == "changes_observed":
        reasons.append('une définition, un échec, un inventaire ou un résultat a changé')
    elif not reasons:
        reasons.append('les rapports ne permettent pas de conclure à une absence de différence')

    if base_report["revision"] == candidate_report["revision"]:
        reasons.append("la même révision est déclarée des deux côtés ; aucun nouveau changement de code n’est attesté")

    return {
        "status": status,
        "revisions": {
            "base": dict(base_report["revision"]),
            "candidate": dict(candidate_report["revision"]),
        },
        "checks": check_results,
        "reasons": _unique(reasons),
    }


def compare(base: Any, candidate: Any) -> Dict[str, Any]:
    """Validate and compare two observation mappings without executing anything."""

    return _compare_validated(
        validate_report(base, 'rapport de base'),
        validate_report(candidate, 'rapport candidat'),
    )


class FrenchArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ReportError("arguments invalides ; consulter --help")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = FrenchArgumentParser(
        add_help=False,
        description=("Comparer deux rapports JSON sans exécuter de commande ni lire de chemin de preuve. "
                     "Code 0 : no_difference_observed, jamais une autorisation de livraison. "
                     "Code 1 : autre résultat de comparaison valide. Code 2 : entrée illisible ou invalide.")
    )
    parser.add_argument("-h", "--help", action="help", help="afficher cette aide et quitter")
    arguments_group = parser.add_argument_group("arguments positionnels")
    arguments_group.add_argument("base", help="fichier JSON des observations de base")
    arguments_group.add_argument("candidate", help="fichier JSON des observations candidates")
    try:
        arguments = parser.parse_args(argv)
        result = _compare_validated(
            load_report(arguments.base),
            load_report(arguments.candidate),
        )
    except (ReportError, OSError, TypeError, ValueError) as error:
        print('compare-checks : entrée invalide : %s' % error, file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "no_difference_observed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
