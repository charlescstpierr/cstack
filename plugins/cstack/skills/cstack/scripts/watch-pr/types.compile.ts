import { parsePrNumber } from "./types.ts";
import type {
  CiClean,
  GitHubMergeAllowed,
  PrContext,
  ReadyPr,
  TerminalVerdict,
} from "./types.ts";

type ReadyVerdict = Extract<TerminalVerdict, { readonly kind: "READY" }>;

const context = {
  owner: "octocat",
  repo: "hello-world",
  number: parsePrNumber(123),
} satisfies PrContext;
const cleanCi = {
  kind: "ci-clean",
  source: "gh-pr-checks",
  all: [
    {
      kind: "passed",
      name: "ci",
      reportedState: "SUCCESS",
      description: "",
      link: "",
      workflow: "",
    },
  ],
  failed: [],
  pending: [],
  hadPreviousPassingCi: false,
  github: {
    kind: "allowed",
    basis: "merge-state",
    mergeStateStatus: "CLEAN",
    headRollupState: "SUCCESS",
  },
} satisfies CiClean;
const readyPr = {
  kind: "ready-pr",
  context,
  headRefOid: "head",
  proof: {
    mergeability: "clear",
    threads: [],
    ci: cleanCi,
    gate: {
      state: "OPEN",
      reviewDecision: "APPROVED",
      draft: "not-draft",
    },
  },
} satisfies ReadyPr;
const { headRefOid: _headRefOid, ...readyWithoutHead } = readyPr;
// @ts-expect-error READY doit nommer le commit dont les checks ont été lus.
const missingReadyHead: ReadyPr = readyWithoutHead;
const ready = {
  schemaVersion: 1,
  sequence: 1,
  observedAt: "2026-07-26T00:00:00.000Z",
  mode: "single",
  kind: "READY",
  terminal: true,
  exitCode: 0,
  scope: { kind: "single", pr: readyPr },
} satisfies ReadyVerdict;

void ready;

// Forme de la PR 179929. Chaque assertion ci-dessous reste une seule instruction
// courte pour qu'un reformatage ne sépare pas la directive de la ligne qui échoue vraiment.
const refused = {
  kind: "allowed",
  basis: "rollup",
  mergeStateStatus: "BLOCKED",
  headRollupState: "FAILURE",
} as const;

// @ts-expect-error BLOCKED avec un rollup échouant est un refus, pas une autorisation.
const refusalIsNotAllowed: GitHubMergeAllowed = refused;

// @ts-expect-error La CI ne peut pas être propre quand GitHub refuse la fusion.
const refusalIsNotClean: CiClean = { ...cleanCi, github: refused };

// @ts-expect-error READY ne peut pas porter le code de sortie de checks échouants.
const readyWithBlockerExit: ReadyVerdict = { ...ready, exitCode: 4 };

const unprovenPr = { kind: "ready-pr", context } as const;

// @ts-expect-error Une ligne READY ouverte doit porter une preuve positive de l’état prêt.
const readyWithoutProof: ReadyPr = unprovenPr;

void refusalIsNotAllowed;
void refusalIsNotClean;
void readyWithBlockerExit;
void readyWithoutProof;
