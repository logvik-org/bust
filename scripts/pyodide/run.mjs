// Install a bust wheel in Pyodide the way the browser does and generate every
// example into OUTPUT_DIR, as `bust FILE -o OUTPUT_DIR -p` would.
// Usage: node scripts/pyodide/run.mjs WHEEL OUTPUT_DIR
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadPyodide } from "pyodide";

// The set docs/getting-started.md lists. The browser leaves out Textual (the
// editor) and docopt (the command line, and PyPI has no wheel of it).
const CORE_DEPENDENCIES = ["json5", "Jinja2", "pylatexenc"];

const [wheel, outputDir] = process.argv.slice(2);
if (!wheel || !outputDir) {
  console.error("Usage: node scripts/pyodide/run.mjs WHEEL OUTPUT_DIR");
  process.exit(2);
}
const repo = fileURLToPath(new URL("../..", import.meta.url));
mkdirSync(outputDir, { recursive: true });

const pyodide = await loadPyodide();
const mounts = {
  "/repo": repo,
  "/dist": path.dirname(path.resolve(wheel)),
  "/out": path.resolve(outputDir),
};
for (const [mountPoint, root] of Object.entries(mounts)) {
  pyodide.FS.mkdirTree(mountPoint);
  pyodide.FS.mount(pyodide.FS.filesystems.NODEFS, { root }, mountPoint);
}

await pyodide.loadPackage("micropip");
const micropip = pyodide.pyimport("micropip");
await micropip.install(CORE_DEPENDENCIES);
await micropip.install.callKwargs(`emfs:/dist/${path.basename(wheel)}`, {
  deps: false,
});

const sys = pyodide.pyimport("sys");
sys.path.append("/repo/scripts/pyodide");
pyodide.pyimport("generate_examples").generate_examples("/repo/example", "/out");
