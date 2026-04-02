#!/usr/bin/env node
/* Resolve a working Python interpreter for the canonical VSIX helper. */

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const helperPath = path.join(__dirname, "package_review_gate_vsix.py");
const helperArgs = process.argv.slice(2);

const candidates =
  process.platform === "win32"
    ? [
        { command: "py", args: ["-3", helperPath, ...helperArgs] },
        { command: "python", args: [helperPath, ...helperArgs] },
        { command: "python3", args: [helperPath, ...helperArgs] },
      ]
    : [
        { command: "python3", args: [helperPath, ...helperArgs] },
        { command: "python", args: [helperPath, ...helperArgs] },
      ];

for (const candidate of candidates) {
  const result = spawnSync(candidate.command, candidate.args, { stdio: "inherit" });

  if (result.error && result.error.code === "ENOENT") {
    continue;
  }

  if (result.error) {
    console.error(`Failed to run ${candidate.command}: ${result.error.message}`);
    process.exit(1);
  }

  process.exit(result.status === null ? 1 : result.status);
}

const tried = candidates
  .map((candidate) => [candidate.command, ...candidate.args.slice(0, 1)].join(" "))
  .join(", ");

console.error(`No supported Python interpreter found. Tried: ${tried}`);
process.exit(1);
