// Install a bust wheel in Pyodide the way the browser does and generate every
// example into OUTPUT_DIR, as `bust FILE -o OUTPUT_DIR -p` would.
// Usage: node scripts/pyodide/run.mjs WHEEL OUTPUT_DIR
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadPyodide } from "pyodide";

const [wheel, outputDir] = process.argv.slice(2);
if (!wheel || !outputDir) {
  console.error("Usage: node scripts/pyodide/run.mjs WHEEL OUTPUT_DIR");
  process.exit(2);
}
const repo = fileURLToPath(new URL("../..", import.meta.url));
mkdirSync(outputDir, { recursive: true });

// SOURCE_DATE_EPOCH pins the time bust writes into the files.
const env = { HOME: "/home/pyodide" };
if (process.env.SOURCE_DATE_EPOCH !== undefined) {
  env.SOURCE_DATE_EPOCH = process.env.SOURCE_DATE_EPOCH;
}
const pyodide = await loadPyodide({ env });
const mounts = {
  "/repo": repo,
  "/dist": path.dirname(path.resolve(wheel)),
  "/out": path.resolve(outputDir),
};
for (const [mountPoint, root] of Object.entries(mounts)) {
  pyodide.FS.mkdirTree(mountPoint);
  pyodide.FS.mount(pyodide.FS.filesystems.NODEFS, { root }, mountPoint);
}

await pyodide.loadPackage(["micropip", "packaging"]);
const micropip = pyodide.pyimport("micropip");
await micropip.install.callKwargs(`emfs:/dist/${path.basename(wheel)}`, {
  deps: false,
});
// The browser leaves out Textual (the editor) and docopt (the command line,
// and PyPI has no wheel of it). docs/getting-started.md lists the rest.
const coreRequirements = pyodide
  .runPython(
    `
from importlib.metadata import requires
from packaging.requirements import Requirement

[
    str(requirement)
    for requirement in map(Requirement, requires("bust"))
    if requirement.marker is None and requirement.name not in ("textual", "docopt")
]
`,
  )
  .toJs();
await micropip.install(coreRequirements);

const sys = pyodide.pyimport("sys");
sys.path.append("/repo/scripts/pyodide");
pyodide.pyimport("generate_examples").generate_examples("/repo/example", "/out");
