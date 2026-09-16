#!/usr/bin/env node
import fs from "node:fs";
import process from "node:process";

const RULES = [
	"Tests alone do not verify a PR. Each PR requires unit, live, and performance evidence.",
	"Les tests seuls ne vérifient pas une PR. Chaque PR exige des preuves unitaires, en situation réelle et de performance.",
];
const LANES = ["within native capacity", "dans la capacité native"];
const SUB_BLOCK_GROUPS = [
	[
		"Depends on.",
		"Files.",
		"Build.",
		"You see.",
		"Verify, unit.",
		"Verify, live.",
		"Verify, performance.",
		"Review gate.",
		"Deliver.",
	],
	[
	"Dépend de.",
	"Fichiers.",
	"Construire.",
	"Tu vois.",
	"Vérifier, unitaire.",
	"Vérifier, réel.",
	"Vérifier, performance.",
	"Barrière de revue.",
	"Livrer.",
	],
];
const [EN_SUB_BLOCKS, FR_SUB_BLOCKS] = SUB_BLOCK_GROUPS;
const ALL_SUB_BLOCKS = SUB_BLOCK_GROUPS.flat();
const PROGRAM_H3_GROUPS = [
	["Start the program", "Assign owners", "Handle each PR", "Verify and deliver each PR", "Boot each live lane"],
	["Démarrer le programme", "Attribuer les responsables", "Traiter chaque PR", "Vérifier et livrer chaque PR", "Démarrer chaque voie réelle"],
];
const PROGRAM_MARKERS = [
	[".cstack/"],
	["native"],
	["authorization", "autorisation"],
];
const HOW_TO_READ_MARKER_GROUPS = [
	[
		"One box is one unit of work",
		"names its evidence",
		"Check a box only when that evidence exists",
		"playbooks/",
		RULES[0],
	],
	[
		"Une case est une unité de travail",
		"nomme sa preuve",
		"Coche une case seulement quand cette preuve existe",
		"playbooks/",
		RULES[1],
	],
];
const PERF_ITEM_GROUPS = [
	["Metric.", "Probe.", "Baseline.", "Rule."],
	["Métrique.", "Sonde.", "Référence.", "Règle."],
];
const H2 = {
	howToRead: ["How to read this", "Comment lire ceci"],
	program: ["Program checklist", "Liste de contrôle du programme"],
	close: ["Close the program", "Fermer le programme"],
};
const BOX = /^\s*- \[[ x]\] (.*)$/;

const file = process.argv[2];
if (!file) {
	console.error("Utilisation: node check-plan.mjs <plan.md>");
	process.exit(2);
}

const raw = fs.readFileSync(file, "utf8").split(/\r?\n/);
const problems = [];
const fail = (line, message) => problems.push(`${file}:${line}: ${message}`);

let start = 0;
if (raw[0] === "---") {
	start = raw.indexOf("---", 1) + 1;
}

const lines = [];
let fence = false;
for (let i = start; i < raw.length; i++) {
	const text = raw[i];
	const n = i + 1;
	if (/^```/.test(text)) fence = !fence;
	lines.push({ n, text, code: fence });
}

const h2 = (l) => (!l.code && l.text.startsWith("## ") ? l.text.slice(3).trim() : null);
const sections = [];
for (const l of lines) {
	const title = h2(l);
	if (title !== null) sections.push({ title, n: l.n, body: [] });
	else if (sections.length) sections.at(-1).body.push(l);
}
const find = (title) => sections.find((s) => s.title === title);
const findAny = (titles) => titles.flatMap((title) => find(title) ?? []).at(0);
const bodyText = (s) => s.body.map((l) => l.text).join("\n");
const boxes = (ls) => ls.filter((l) => !l.code && BOX.test(l.text)).map((l) => ({ n: l.n, text: l.text.match(BOX)[1] }));
const markerSetFor = (text, groups) => groups.find((markers) => markers.every((marker) => text.includes(marker))) ?? groups[1];
const startsWithAny = (text, values) => values.some((value) => text.startsWith(value));
const hasAny = (text, values) => values.some((value) => text.includes(value));

const h1 = lines.findIndex((l) => !l.code && l.text.startsWith("# "));
if (h1 === -1) fail(1, "titre H1 manquant");
const howToRead = findAny(H2.howToRead);
if (!howToRead) fail(1, 'section "## Comment lire ceci" manquante');
if (h1 !== -1 && howToRead) {
	const intro = lines.slice(h1 + 1).filter((l) => l.n < howToRead.n && l.text.trim() !== "");
	if (intro.length >= 10) fail(lines[h1].n, `l’introduction fait ${intro.length} lignes; moins de dix sont requises`);
	for (const marker of markerSetFor(bodyText(howToRead), HOW_TO_READ_MARKER_GROUPS)) {
		if (!bodyText(howToRead).includes(marker)) fail(howToRead.n, `Comment lire ceci ne contient pas "${marker}"`);
	}
}

const program = findAny(H2.program);
if (!program) fail(1, 'section "## Liste de contrôle du programme" manquante');
else {
	const h3s = program.body.filter((l) => !l.code && l.text.startsWith("### ")).map((l) => l.text.slice(4).trim());
	const expectedH3s = markerSetFor(h3s.join("\n"), PROGRAM_H3_GROUPS);
	let cursor = 0;
	for (const name of expectedH3s) {
		const at = h3s.findIndex((t, i) => i >= cursor && t.startsWith(name));
		if (at === -1) fail(program.n, `Liste de contrôle du programme ne contient pas "### ${name}" dans l’ordre`);
		else cursor = at + 1;
	}
	for (const marker of PROGRAM_MARKERS) {
		const text = bodyText(program);
		const ok = Array.isArray(marker)
			? marker.some((value) => text.includes(value))
			: marker instanceof RegExp
				? marker.test(text)
				: text.includes(marker);
		if (!ok) fail(program.n, `Liste de contrôle du programme ne contient pas "${Array.isArray(marker) ? marker.at(-1) : marker}"`);
	}
}

const close = findAny(H2.close);
if (!close) fail(1, 'section "## Fermer le programme" manquante');
const programIndex = sections.indexOf(program);
const closeIndex = sections.indexOf(close);
const prSections = programIndex === -1 || closeIndex === -1 ? [] : sections.slice(programIndex + 1, closeIndex);
if (prSections.length === 0) fail(1, "aucune section de PR entre Liste de contrôle du programme et Fermer le programme");

const report = [];
for (const pr of prSections) {
	const heads = [];
	for (const l of pr.body) {
		if (l.code) continue;
		const m = l.text.match(/^\*\*([^*]+)\*\*(.*)$/);
		if (m && ALL_SUB_BLOCKS.includes(m[1])) heads.push({ name: m[1], n: l.n, rest: m[2].trim(), lines: [] });
		else if (heads.length) heads.at(-1).lines.push(l);
	}
	const names = heads.map((h) => h.name);
	const subBlocks = names.includes(FR_SUB_BLOCKS[0]) ? FR_SUB_BLOCKS : EN_SUB_BLOCKS;
	if (names.join("|") !== subBlocks.join("|")) {
		fail(pr.n, `${pr.title}: les sous-blocs sont [${names.join(", ")}], attendu [${subBlocks.join(", ")}]`);
	}
	const block = (name) => heads.find((h) => h.name === name);
	const counts = {};
	for (const h of heads) counts[h.name] = boxes(h.lines).length;

	const depends = block(subBlocks[0]);
	if (depends && depends.rest === "") fail(depends.n, `${pr.title}: Dépend de ne nomme rien`);
	for (const name of [subBlocks[1], subBlocks[2], subBlocks[3], subBlocks[4], subBlocks[8]]) {
		const b = block(name);
		if (b && boxes(b.lines).length === 0) fail(b.n, `${pr.title}: ${name} n’a aucune case`);
	}
	for (const name of [subBlocks[4], subBlocks[5], subBlocks[6]]) {
		const b = block(name);
		if (b && !startsWithAny(b.rest, RULES)) fail(b.n, `${pr.title}: ${name} ne commence pas par la règle`);
	}

	const live = block(subBlocks[5]);
	if (live) {
		if (!hasAny(live.rest, LANES)) fail(live.n, `${pr.title}: Vérifier, réel ne contient pas "${LANES[1]}"`);
		const lanes = boxes(live.lines).map((b) => ({ ...b, m: b.text.match(/^(?:Lane|Voie) (\d+)\. /) }));
		const numbers = lanes.filter((b) => b.m).map((b) => Number(b.m[1])).sort((a, b) => a - b);
		if (numbers.join(",") !== "1,2,3,4,5,6,7,8,9,10") fail(live.n, `${pr.title}: les voies sont [${numbers.join(",")}], attendu 1 à 10`);
		for (const lane of lanes) {
			if (!lane.m) fail(lane.n, `${pr.title}: la case réelle n’est pas une voie`);
			else if (/^(?:Lane|Voie) \d+\. n\/a:\s*\S/.test(lane.text)) continue;
			else if (!/(?:Save|Enregistrer) `[^`]+`/.test(lane.text)) fail(lane.n, `${pr.title}: la voie ${lane.m[1]} ne nomme aucun artefact de preuve`);
			else if (!hasAny(lane.text, ["Pass when", "Réussit quand"])) fail(lane.n, `${pr.title}: la voie ${lane.m[1]} n’a pas de prédicat de réussite`);
		}
	}

	const perf = block(subBlocks[6]);
	if (perf) {
		const items = boxes(perf.lines).map((b) => b.text.split(" ")[0]);
		const perfItems = items.includes(PERF_ITEM_GROUPS[1][0]) ? PERF_ITEM_GROUPS[1] : PERF_ITEM_GROUPS[0];
		if (items.join("|") !== perfItems.join("|")) fail(perf.n, `${pr.title}: les cases perf sont [${items.join(", ")}], attendu [${perfItems.join(", ")}]`);
	}

	const gate = block(subBlocks[7]);
	if (gate) {
		const gateBoxes = boxes(gate.lines);
		if (gate.rest.startsWith("None.") || gate.rest.startsWith("Aucune.")) {
			if (gateBoxes.length) fail(gate.n, `${pr.title}: Barrière de revue annonce aucune barrière mais contient des cases`);
		} else {
			const text = gate.lines.map((l) => l.text).join("\n");
			if (gateBoxes.length === 0) fail(gate.n, `${pr.title}: Barrière de revue n’a aucune case`);
			for (const words of [["screenshot", "capture"], ["video", "vidéo"], ["operator", "opérateur"]]) {
				if (!hasAny(text, words)) fail(gate.n, `${pr.title}: Barrière de revue ne contient pas "${words.at(-1)}"`);
			}
		}
	}

	const total = boxes(pr.body).length;
	const cells = subBlocks.filter((s) => s !== subBlocks[0]).map((s) => `${s.replace(/[ ,.]+/g, "-").replace(/-$/, "").toLowerCase()}=${counts[s] ?? 0}`);
	report.push(`${pr.title}  boxes=${total}  ${cells.join(" ")}`);
}

if (closeIndex !== -1) {
	const tail = sections.slice(closeIndex + 1);
	for (const s of tail) {
		if (!startsWithAny(s.title, ["Appendix", "Annexe"])) fail(s.n, `"## ${s.title}" après Fermer le programme n’est pas une annexe`);
	}
	if (!tail.some((s) => hasAny(s.title, ["Prototype evidence", "Preuve du prototype"]))) fail(close.n, 'section "## Annexe ... Preuve du prototype" manquante');
}

for (const line of report) console.log(line);
console.log(`${prSections.length} sections de PR, ${problems.length} problèmes`);
for (const p of problems) console.error(p);
process.exit(problems.length ? 1 : 0);
