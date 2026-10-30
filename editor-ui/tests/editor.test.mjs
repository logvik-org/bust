// The editor against bust itself: a bust bridge process over stdio, as an
// editor on the desktop runs it. Set PYTHON to a Python that has bust.
import { after, before, beforeEach, describe, test } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { createInterface } from "node:readline";
import { Window } from "happy-dom";
import { BustBridge, RegisterMapEditor } from "../dist/index.js";

const window = new Window();
for (const name of ["document", "Node", "HTMLElement", "HTMLInputElement", "Event", "KeyboardEvent"]) {
  globalThis[name] = window[name];
}

const example = readFileSync(new URL("../../example/example_axi.json", import.meta.url), "utf8");

function startBust() {
  const child = spawn(process.env.PYTHON ?? "python3", ["-m", "bust.editing.bridge"], {
    cwd: new URL("../..", import.meta.url),
    stdio: ["pipe", "pipe", "inherit"],
  });
  const waiting = new Map();
  createInterface({ input: child.stdout }).on("line", (line) => {
    const { id } = JSON.parse(line);
    waiting.get(id)(line);
    waiting.delete(id);
  });
  const transport = (request) =>
    new Promise((resolve) => {
      waiting.set(JSON.parse(request).id, resolve);
      child.stdin.write(request + "\n");
    });
  return { child, transport };
}

function button(container, name) {
  return [...container.querySelectorAll("button")].find((candidate) => candidate.textContent === name);
}

function treeNode(container, name) {
  return [...container.querySelectorAll(".bust-editor-node")].find(
    (node) => node.querySelector(".bust-editor-name").textContent === name,
  );
}

function treeNames(container) {
  return [...container.querySelectorAll(".bust-editor-node .bust-editor-name")].map((name) => name.textContent);
}

function change(input, value) {
  if (input.type === "checkbox") {
    input.checked = value;
  } else {
    input.value = value;
  }
  input.dispatchEvent(new Event("change"));
}

describe("RegisterMapEditor", () => {
  let bust;
  let container;
  let editor;
  let changes;

  before(() => {
    bust = startBust();
  });

  after(() => bust.child.kill());

  beforeEach(async () => {
    container = document.createElement("div");
    changes = [];
    editor = new RegisterMapEditor(container, new BustBridge(bust.transport), {
      onChange: (state) => changes.push(state),
    });
    await editor.open(example);
  });

  test("lists the registers with the addresses bust gives them", () => {
    const names = treeNames(container);
    assert.deepEqual(names.slice(0, 4), ["Bus", "example_axi", "reg0", "reg1"]);
    assert.equal(treeNode(container, "reg1").querySelector(".bust-editor-meta").textContent, "0x00000004");
    assert.ok(names.includes("field3"));
  });

  test("a change in the form goes to bust and comes back as text", async () => {
    treeNode(container, "reg1").click();
    await editor.idle();
    const sw = container.querySelector("[data-key='sw'] select");
    change(sw, "ro");
    await editor.idle();
    assert.equal(editor.state.data.module.register[1].sw, "ro");
    assert.match(changes.at(-1).text, /"sw": "ro"/);
    assert.equal(button(container, "Undo").disabled, false);
  });

  test("a change bust rejects stays in the form with bust's problem", async () => {
    treeNode(container, "reg1").click();
    const name = container.querySelector("[data-key='name'] input");
    change(name, "reg0");
    await editor.idle();
    assert.equal(editor.state.data.module.register[1].name, "reg1");
    assert.equal(name.value, "reg0");
    assert.ok(container.querySelector(".bust-editor-rejected"));
  });

  test("problems with a path show next to their input", async () => {
    treeNode(container, "reg1").click();
    const address = container.querySelector("[data-key='address'] input");
    change(address, "zz");
    await editor.idle();
    const row = container.querySelector("[data-key='address']");
    assert.ok(row.classList.contains("bust-editor-invalid"));
    assert.ok(row.querySelector(".bust-editor-problem").textContent.length > 0);
  });

  test("adding a register puts it after the selected one", async () => {
    treeNode(container, "reg1").click();
    await editor.idle();
    button(container, "Add register").click();
    await editor.idle();
    const names = editor.state.data.module.register.map((register) => register.name);
    assert.deepEqual(names.slice(0, 3), ["reg0", "reg1", "reg12"]);
    assert.equal(container.querySelector("[aria-current='true'] .bust-editor-name").textContent, "reg12");
  });

  test("adding a field turns a register into a fields register", async () => {
    treeNode(container, "reg0").click();
    await editor.idle();
    button(container, "Add field").click();
    await editor.idle();
    const register = editor.state.data.module.register[0];
    assert.equal(register.type, "fields");
    assert.deepEqual(register.fields, [{ name: "field0", type: "bit" }]);
    assert.equal(container.querySelector("[aria-current='true'] .bust-editor-name").textContent, "field0");
  });

  test("moving and removing a register, then undoing", async () => {
    treeNode(container, "reg1").click();
    await editor.idle();
    button(container, "Move up").click();
    await editor.idle();
    assert.deepEqual(
      editor.state.data.module.register.slice(0, 2).map((register) => register.name),
      ["reg1", "reg0"],
    );
    button(container, "Remove").click();
    await editor.idle();
    assert.equal(editor.state.data.module.register[0].name, "reg0");
    button(container, "Undo").click();
    await editor.idle();
    button(container, "Undo").click();
    await editor.idle();
    assert.equal(editor.state.text, example);
  });

  test("the register's fields show by bit", async () => {
    treeNode(container, "reg7").click();
    await editor.idle();
    const cells = [...container.querySelectorAll(".bust-editor-bits button")];
    assert.deepEqual(
      cells.map((cell) => cell.title),
      ["field0 [0]", "field1 [4:1]", "field2 [5]", "field3 [20:6]"],
    );
    assert.equal(cells[1].style.gridColumn, "28 / 32");
  });
});
