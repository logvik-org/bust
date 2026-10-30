# bust-editor

The register map editor of [bust](https://github.com/logvik-org/bust), for the web. It shows a register map as a tree of the bus, the module, its registers and their fields, with a form for the one selected, built from bust's JSON Schema. [cloudbust](https://cloudbust.netlify.app) runs it with bust in the browser.

The editor never changes a register map itself. Every change goes to bust as JSON Patch operations, and bust either makes it or rejects it with its problems, which the editor shows next to the values they are about. So the editor only ever holds register maps bust accepts.

## Use

```ts
import { BustBridge, RegisterMapEditor } from "bust-editor";
import "bust-editor/style.css";

const bridge = new BustBridge(transport);
const editor = new RegisterMapEditor(container, bridge, {
  onChange: (state) => console.log(state.text),
});
await editor.open(registerMapText);
```

`transport` takes one JSON-RPC 2.0 request as a string and resolves to bust's response. bust answers these in `bust.editing.bridge`: call `EditorBridge().handle(request)` in Python (Pyodide in a browser), or run `python -m bust.editing.bridge` and exchange one message per line over stdin and stdout. The methods are listed in [bridge.py](../bust/editing/bridge.py).

The look follows bust's documentation, in light and dark. Set the `--bust-*` variables named at the top of `style.css` to theme it.

## Develop

Node.js 22.12 or newer, and a Python with bust installed for the tests:

```sh
pip install -e ..
npm ci
PYTHON=python npm test
```

`npm test` builds `dist/` and runs the editor in happy-dom against a bust bridge process.

## Release

Set `version` in `package.json` and push a tag `editor-ui-vX.Y.Z`. The Editor UI workflow tests the package and publishes it to npm with trusted publishing.
