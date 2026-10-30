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
for (const name of ["document", "Node", "HTMLElement", "HTMLInputElement", "HTMLButtonElement", "Event", "KeyboardEvent"]) {
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

function row(container, pane, name) {
  return [...container.querySelectorAll(`.bust-editor-${pane} tbody tr`)].find(
    (candidate) => candidate.querySelector(".bust-editor-name").textContent === name,
  );
}

function names(container, pane) {
  return [...container.querySelectorAll(`.bust-editor-${pane} tbody .bust-editor-name`)].map((cell) => cell.textContent);
}

function dialog(container) {
  return container.querySelector("dialog.bust-editor-dialog");
}

function input(container, key) {
  return dialog(container).querySelector(`[data-key='${key}'] :is(input, select, textarea)`);
}

async function submit(container, editor) {
  dialog(container).querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
  await new Promise((resolve) => setTimeout(resolve, 0));
  await editor.idle();
  await new Promise((resolve) => setTimeout(resolve, 0));
}

function menuItem(container, label) {
  return [...container.querySelectorAll(".bust-editor-menu [role='menuitem']")].find(
    (item) => item.firstChild.textContent === label,
  );
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
    assert.deepEqual(names(container, "registers").slice(0, 3), ["reg0", "reg1", "reg2"]);
    assert.equal(row(container, "registers", "reg1").firstChild.textContent, "0x00000004");
    assert.equal(row(container, "registers", "reg7").children[4].textContent, "RW/R");
  });

  test("a change in a dialog goes to bust and comes back as text", async () => {
    row(container, "registers", "reg1").dispatchEvent(new Event("dblclick"));
    assert.equal(dialog(container).querySelector("h2").textContent, "Register reg1");
    input(container, "sw").value = "ro";
    await submit(container, editor);
    assert.equal(dialog(container).open, false);
    assert.equal(editor.state.data.module.register[1].sw, "ro");
    assert.match(changes.at(-1).text, /"sw": "ro"/);
    assert.equal(button(container, "Undo").disabled, false);
  });

  test("a change bust rejects keeps the dialog open with bust's problem", async () => {
    row(container, "registers", "reg1").dispatchEvent(new Event("dblclick"));
    input(container, "name").value = "reg0";
    await submit(container, editor);
    assert.equal(dialog(container).open, true);
    assert.equal(editor.state.data.module.register[1].name, "reg1");
    assert.match(dialog(container).querySelector(".bust-editor-dialog-problems").textContent, /reg0/);
  });

  test("problems with a path show next to their value", async () => {
    row(container, "registers", "reg1").dispatchEvent(new Event("dblclick"));
    input(container, "address").value = "zz";
    await submit(container, editor);
    const address = dialog(container).querySelector("[data-key='address']");
    assert.ok(address.classList.contains("bust-editor-invalid"));
    assert.ok(address.querySelector(".bust-editor-problem").textContent.length > 0);
  });

  test("adding a register from the toolbar puts it last and selects it", async () => {
    button(container, "Add register").click();
    assert.equal(input(container, "name").value, "reg12");
    await submit(container, editor);
    assert.equal(names(container, "registers").at(-1), "reg12");
    assert.equal(container.querySelector(".bust-editor-registers tr[aria-selected='true'] .bust-editor-name").textContent, "reg12");
  });

  test("the first field turns a register into a fields register", async () => {
    row(container, "registers", "reg0").click();
    button(container, "Add field").click();
    input(container, "name").value = "enable";
    await submit(container, editor);
    const register = editor.state.data.module.register[0];
    assert.equal(register.type, "fields");
    assert.deepEqual(register.fields, [{ name: "enable", type: "bit" }]);
    assert.ok(!("reset" in register));
    assert.equal(container.querySelector(".bust-editor-detail tr[aria-selected='true'] .bust-editor-name").textContent, "enable");
  });

  test("a register's pop-up menu moves and removes it, and undo brings it back", async () => {
    row(container, "registers", "reg1").dispatchEvent(new window.MouseEvent("contextmenu", { clientX: 10, clientY: 10, cancelable: true }));
    assert.equal(container.querySelector(".bust-editor-menu").hidden, false);
    menuItem(container, "Move up").click();
    await editor.idle();
    assert.deepEqual(names(container, "registers").slice(0, 2), ["reg1", "reg0"]);
    row(container, "registers", "reg1").querySelector(".bust-editor-more").click();
    menuItem(container, "Remove register").click();
    await editor.idle();
    assert.equal(names(container, "registers")[0], "reg0");
    button(container, "Undo").click();
    await editor.idle();
    button(container, "Undo").click();
    await editor.idle();
    assert.equal(editor.state.text, example);
  });

  test("a field's menu edits its named values", async () => {
    row(container, "registers", "reg7").click();
    row(container, "detail", "field1").dispatchEvent(new window.MouseEvent("contextmenu", { clientX: 10, clientY: 10, cancelable: true }));
    menuItem(container, "Named values…").click();
    button(dialog(container), "Add value").click();
    // bust wants field1's reset, 0xB, to be one of the named values.
    dialog(container).querySelector('[aria-label="Value 1"]').value = "11";
    await submit(container, editor);
    assert.deepEqual(editor.state.data.module.register[7].fields[1].enums, [{ name: "VALUE0", value: 11 }]);
  });

  test("the register's fields show by bit, as in the documentation", () => {
    row(container, "registers", "reg7").click();
    const boxes = [...container.querySelectorAll(".bust-editor-diagram-segment")];
    assert.deepEqual(
      boxes.map((box) => box.querySelector(".bust-editor-diagram-box").textContent),
      ["", "field3", "field2", "field1", "field0"],
    );
    assert.equal(boxes[3].style.gridColumn, "28 / 32");
    boxes[3].querySelector("button").click();
    assert.equal(container.querySelector(".bust-editor-keys h3").textContent, "Field field1 of reg7");
  });
});
