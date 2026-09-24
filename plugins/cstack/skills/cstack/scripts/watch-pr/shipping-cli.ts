import { readFile } from "node:fs/promises";
import { Command, CommanderError } from "commander";
import { object, parseContext } from "./landing.ts";
import {
  cancelPending,
  GhShippingService,
  inspectLanding,
  parseLandingRecord,
  type ShippingResult,
} from "./shipping.ts";

export async function main(argv: readonly string[]): Promise<number> {
  let result: ShippingResult | undefined;
  const service = new GhShippingService();
  const cli = new Command("ship-pr").exitOverride();
  cli.description(
    "Inspecte une révision d'atterrissage ou annule ses mécanismes de fusion en attente. Ne fusionne ni ne réécrit les branches."
  );
  cli
    .command("inspect")
    .requiredOption("--repo <owner/repo>")
    .requiredOption("--pr <number>")
    .action(async (options: { repo: string; pr: string }) => {
      const parts = options.repo.split("/");
      if (parts.length !== 2)
        throw new Error("--repo doit avoir la forme owner/repo");
      const context = parseContext({
        owner: parts[0],
        repo: parts[1],
        number: Number(options.pr),
      });
      result = await inspectLanding(service, context);
    });
  cli
    .command("cancel-pending")
    .requiredOption(
      "--record <file>",
      "JSON produit par inspect ou par une cancellation réussie"
    )
    .action(async (options: { record: string }) => {
      const input = object(
        JSON.parse(await readFile(options.record, "utf8")),
        "inspection sauvegardée"
      );
      if (input.kind !== "inspected" && input.kind !== "cancelled")
        throw new Error("record doit contenir une inspection réussie");
      result = await cancelPending(
        service,
        parseLandingRecord(input.record)
      );
    });
  try {
    await cli.parseAsync(argv, { from: "user" });
    if (!result) return 64;
  } catch (error) {
    if (error instanceof CommanderError) return error.exitCode === 0 ? 0 : 64;
    result = {
      kind: "unavailable",
      detail: error instanceof Error ? error.message : String(error),
    };
  }
  process.stdout.write(`${JSON.stringify(result)}\n`);
  return result.kind === "inspected" || result.kind === "cancelled" ? 0 : 1;
}
