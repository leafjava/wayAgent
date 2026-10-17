// TokenTruth · harness 入口
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const isWindows = process.platform === "win32";
const venvPython = path.join(root, ".venv", isWindows ? "Scripts/python.exe" : "bin/python");

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: root,
    env: { ...process.env, PYTHONUTF8: "1", ...options.env },
    stdio: options.capture ? "pipe" : "inherit",
    encoding: "utf8",
  });
  if (options.capture) return result;
  if (result.error) { console.error(result.error.message); process.exit(1); }
  if (result.status !== 0) process.exit(result.status ?? 1);
  return result;
}

function pythonCandidates(includeVenv = true) {
  const candidates = [];
  if (includeVenv && existsSync(venvPython)) candidates.push({ command: venvPython, prefix: [] });
  if (process.env.PYTHON) candidates.push({ command: process.env.PYTHON, prefix: [] });
  if (isWindows) candidates.push({ command: "py", prefix: ["-3"] });
  candidates.push({ command: "python3", prefix: [] }, { command: "python", prefix: [] });
  return candidates;
}

function findPython(includeVenv = true) {
  for (const candidate of pythonCandidates(includeVenv)) {
    const probe = run(candidate.command, [...candidate.prefix, "--version"], { capture: true });
    if (!probe.error && probe.status === 0) return candidate;
  }
  console.error("未找到 Python 3.10+");
  process.exit(1);
}

function py(args, options = {}) {
  return run(findPython(true).command, [...findPython(true).prefix, ...args], options);
}

const command = process.argv[2];

switch (command) {
  case "install": {
    const base = existsSync(venvPython) ? { command: venvPython, prefix: [] } : findPython(false);
    if (!existsSync(venvPython)) run(base.command, [...base.prefix, "-m", "venv", ".venv"]);
    run(venvPython, ["-m", "pip", "install", "-r", "requirements-harness.txt"]);
    console.log("Harness dependencies installed");
    break;
  }
  case "dev":
    py(["tools/dev_server.py"]);
    break;
  case "test":
    py(["-m", "unittest", "discover", "-s", "tests/harness", "-p", "test_*.py", "-v"]);
    break;
  case "check":
    py(["-m", "compileall", "-q", "tools", "tests/harness", "src", "web_app.py"]);
    py(["-m", "unittest", "discover", "-s", "tests/harness", "-p", "test_*.py", "-v"]);
    break;
  case "demo":
    py(["tools/smoke_test.py", "--pretty"]);
    break;
  case "chain:deploy":
    py(["scripts/deploy.py"]);
    break;
  case "chain:seed":
    py(["scripts/seed_projects.py"]);
    break;
  default:
    console.error("Usage: node tools/harness.mjs <install|dev|test|check|demo|chain:deploy|chain:seed>");
    process.exit(2);
}
