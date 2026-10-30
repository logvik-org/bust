import {
  ACCESS_KEYS,
  ADVANCED_KEYS,
  definitionOf,
  inputKindOf,
  labelOf,
  parseNumber,
  placeholderOf,
  type NodeKind,
} from "./schema.js";
import { insertAt, move, removeAt, setFieldType, setKey, setRegisterType, uniqueName } from "./operations.js";
import type {
  AcceptedState,
  BustBridge,
  EditorState,
  JsonObject,
  JsonSchema,
  JsonValue,
  Operation,
  Problem,
  ValuePath,
} from "./protocol.js";

export type EditorOptions = {
  // Called with every register map bust accepts, after each change.
  onChange?: (state: AcceptedState) => void;
};

type TreeNode = { kind: NodeKind; path: ValuePath; label: string; meta: string; children: TreeNode[] };

const REGISTERS: ValuePath = ["module", "register"];

let nextEditorId = 0;

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attributes: Record<string, string> = {},
  ...children: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const created = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    created.setAttribute(name, value);
  }
  created.append(...children);
  return created;
}

function samePath(a: ValuePath, b: ValuePath): boolean {
  return a.length === b.length && a.every((token, index) => token === b[index]);
}

function startsWith(path: ValuePath, prefix: ValuePath): boolean {
  return prefix.length <= path.length && prefix.every((token, index) => token === path[index]);
}

function valueAt(data: JsonValue, path: ValuePath): JsonValue | undefined {
  let current: JsonValue | undefined = data;
  for (const token of path) {
    if (current === null || typeof current !== "object") {
      return undefined;
    }
    current = (current as Record<string, JsonValue>)[token as string];
  }
  return current;
}

function hex(value: number, digits: number): string {
  return "0x" + value.toString(16).toUpperCase().padStart(digits, "0");
}

function bits(low: number, high: number): string {
  return low === high ? `[${low}]` : `[${high}:${low}]`;
}

// A tree of the bus, the module, its registers and their fields, next to a
// form for the one selected. Every change goes to bust as JSON Patch, and the
// editor shows only register maps bust accepts. A change bust rejects leaves
// the form as typed, with bust's problems next to the values they are about.
export class RegisterMapEditor {
  private schema?: JsonSchema;
  private accepted?: AcceptedState;
  private problems: Problem[] = [];
  private selected: ValuePath = ["module"];
  // The key of the selected object the last change from the form set. A
  // problem bust gives without a place is shown there.
  private editedKey?: string;
  private queue: Promise<unknown> = Promise.resolve();
  private readonly id = `bust-editor-${nextEditorId++}`;
  private readonly toolbar = element("div", { class: "bust-editor-toolbar", role: "toolbar", "aria-label": "Register map" });
  private readonly tree = element("nav", { class: "bust-editor-tree", "aria-label": "Registers" });
  private readonly form = element("form", { class: "bust-editor-form" });
  private readonly messages = element("div", { class: "bust-editor-messages", role: "status", "aria-live": "polite" });

  constructor(
    container: HTMLElement,
    private readonly bridge: BustBridge,
    private readonly options: EditorOptions = {},
  ) {
    container.classList.add("bust-editor");
    container.replaceChildren(
      this.toolbar,
      element("div", { class: "bust-editor-body" }, this.tree, element("div", { class: "bust-editor-detail" }, this.messages, this.form)),
    );
    this.form.addEventListener("submit", (event) => event.preventDefault());
    container.addEventListener("keydown", (event) => this.onKey(event));
  }

  get state(): AcceptedState | undefined {
    return this.accepted;
  }

  // Starts editing the register map in `text`. If bust rejects it, the
  // editor keeps what it had and the state lists bust's problems.
  open(text: string): Promise<EditorState> {
    return this.run(async () => {
      this.selected = ["module"];
      return this.bridge.call("open", { text });
    });
  }

  create(bus: JsonObject, module: JsonObject): Promise<EditorState> {
    return this.run(async () => {
      this.selected = ["module"];
      return this.bridge.call("new", { bus, module });
    });
  }

  apply(operations: Operation[], select?: ValuePath): Promise<EditorState> {
    return this.run(async () => {
      const state = await this.bridge.call("apply", { operations });
      if (state.accepted && select) {
        this.selected = select;
      }
      return state;
    });
  }

  // Resolves when every change made so far has come back from bust.
  async idle(): Promise<void> {
    await this.queue;
  }

  undo(): Promise<EditorState> {
    return this.run(() => this.bridge.call("undo", {}));
  }

  redo(): Promise<EditorState> {
    return this.run(() => this.bridge.call("redo", {}));
  }

  // One request at a time, so that quick changes reach bust in order.
  private run(request: () => Promise<EditorState>): Promise<EditorState> {
    const result = this.queue.then(async () => {
      this.schema ??= await this.bridge.call("schema", {});
      const state = await request();
      this.show(state);
      return state;
    });
    this.queue = result.catch(() => undefined);
    return result;
  }

  private show(state: EditorState): void {
    if (!state.accepted) {
      this.problems = state.problems;
      this.renderMessages();
      this.renderTree();
      this.markProblemsInForm();
      return;
    }
    this.accepted = state;
    this.problems = [];
    this.editedKey = undefined;
    if (valueAt(state.data, this.selected) === undefined) {
      this.selected = this.nearestExisting(this.selected);
    }
    this.render();
    this.options.onChange?.(state);
  }

  private nearestExisting(path: ValuePath): ValuePath {
    const data = this.accepted!.data;
    const parent = path.slice(0, -1);
    const index = path[path.length - 1];
    if (typeof index === "number" && index > 0 && valueAt(data, [...parent, index - 1]) !== undefined) {
      return [...parent, index - 1];
    }
    return parent.length > 1 ? this.nearestExisting(parent.slice(0, -1)) : ["module"];
  }

  private render(): void {
    this.renderToolbar();
    this.renderTree();
    this.renderForm();
    this.renderMessages();
  }

  private renderToolbar(): void {
    const state = this.accepted!;
    const kind = this.selectedKind();
    const index = this.selected[this.selected.length - 1];
    const siblings = kind === "register" || kind === "field" ? (valueAt(state.data, this.selected.slice(0, -1)) as JsonValue[]) : [];
    const button = (label: string, enabled: boolean, action: () => void, shortcut?: string) => {
      const created = element("button", { type: "button" }, label);
      created.disabled = !enabled;
      if (shortcut) {
        created.setAttribute("aria-keyshortcuts", shortcut);
      }
      created.addEventListener("click", action);
      return created;
    };
    this.toolbar.replaceChildren(
      element(
        "div",
        { class: "bust-editor-group" },
        button("Undo", state.canUndo, () => this.undo(), "Control+Z"),
        button("Redo", state.canRedo, () => this.redo(), "Control+Shift+Z"),
      ),
      element(
        "div",
        { class: "bust-editor-group" },
        button("Add register", true, () => this.addRegister()),
        button("Add field", kind === "register" || kind === "field", () => this.addField()),
      ),
      element(
        "div",
        { class: "bust-editor-group" },
        button("Move up", typeof index === "number" && index > 0, () => this.moveSelected(-1)),
        button("Move down", typeof index === "number" && index < siblings.length - 1, () => this.moveSelected(1)),
        button("Remove", kind === "register" || kind === "field", () => this.removeSelected()),
      ),
    );
  }

  private selectedKind(): NodeKind {
    return this.kindOf(this.selected);
  }

  private kindOf(path: ValuePath): NodeKind {
    if (path[0] === "bus") {
      return "bus";
    }
    return (["module", "module", "register", "register", "field"] as NodeKind[])[path.length - 1] ?? "field";
  }

  private nodes(): TreeNode[] {
    const { data, layout } = this.accepted!;
    const bus = data.bus as JsonObject;
    const module = data.module as JsonObject;
    const registers = module.register as JsonObject[];
    const digits = Math.ceil(Number(bus.addr_width) / 4) || 4;
    return [
      { kind: "bus", path: ["bus"], label: "Bus", meta: String(bus.type), children: [] },
      {
        kind: "module",
        path: ["module"],
        label: String(module.name),
        meta: "module",
        children: registers.map((register, index) => {
          const placed = layout[String(register.name)];
          const fields = (register.fields as JsonObject[] | undefined) ?? [];
          return {
            kind: "register",
            path: [...REGISTERS, index],
            label: String(register.name),
            meta: placed ? hex(placed.address, digits) : "",
            children: fields.map((field, fieldIndex) => {
              const span = placed?.fields[String(field.name)];
              return {
                kind: "field",
                path: [...REGISTERS, index, "fields", fieldIndex],
                label: String(field.name),
                meta: span ? bits(span[0], span[1]) : "",
                children: [],
              };
            }),
          };
        }),
      },
    ];
  }

  // The node a problem belongs to: the deepest one whose path leads to it.
  private ownerOf(problem: Problem, nodes: TreeNode[]): ValuePath | undefined {
    for (const node of nodes) {
      if (startsWith(problem.path, node.path)) {
        return this.ownerOf(problem, node.children) ?? node.path;
      }
    }
    return undefined;
  }

  private renderTree(): void {
    if (!this.accepted) {
      return;
    }
    const nodes = this.nodes();
    const owners = this.problems.map((problem) => this.ownerOf(problem, nodes)).filter((path) => path !== undefined);
    const item = (node: TreeNode): HTMLLIElement => {
      const button = element(
        "button",
        { type: "button", class: `bust-editor-node bust-editor-${node.kind}` },
        element("span", { class: "bust-editor-meta" }, node.meta),
        element("span", { class: "bust-editor-name" }, node.label),
      );
      if (samePath(node.path, this.selected)) {
        button.setAttribute("aria-current", "true");
      }
      if (owners.some((owner) => samePath(owner, node.path))) {
        button.classList.add("bust-editor-invalid");
      }
      button.addEventListener("click", () => this.select(node.path));
      const created = element("li", {}, button);
      if (node.children.length > 0) {
        created.append(element("ul", {}, ...node.children.map(item)));
      }
      return created;
    };
    this.tree.replaceChildren(element("ul", {}, ...nodes.map(item)));
  }

  private select(path: ValuePath): void {
    this.selected = path;
    this.problems = [];
    this.editedKey = undefined;
    this.render();
    this.form.querySelector<HTMLElement>("input, select, textarea")?.focus();
  }

  private renderMessages(): void {
    const items: HTMLElement[] = [];
    if (this.problems.length > 0) {
      items.push(
        element("p", { class: "bust-editor-rejected" }, "bust did not make this change:"),
        element(
          "ul",
          { class: "bust-editor-problems" },
          ...this.problems.map((problem) =>
            element("li", {}, problem.location ? `${problem.location}: ${problem.message}` : problem.message),
          ),
        ),
      );
    }
    const warnings = this.accepted?.warnings ?? [];
    if (warnings.length > 0) {
      items.push(element("ul", { class: "bust-editor-warnings" }, ...warnings.map((warning) => element("li", {}, `Ignored: ${warning}`))));
    }
    this.messages.replaceChildren(...items);
  }

  private renderForm(): void {
    const kind = this.selectedKind();
    const object = valueAt(this.accepted!.data, this.selected) as JsonObject;
    const definition = definitionOf(this.schema!, kind);
    const keys = Object.keys(definition.properties ?? {}).filter((key) => this.isShown(kind, key, object));
    const rows = (wanted: string[]) =>
      wanted.map((key) => this.row(kind, object, key, definition.properties![key], definition.required ?? []));
    const children: Node[] = [this.heading(kind, object), ...rows(keys.filter((key) => !ADVANCED_KEYS.has(key)))];
    const advanced = keys.filter((key) => ADVANCED_KEYS.has(key));
    if (advanced.length > 0) {
      const details = element("details", {}, element("summary", {}, "More access options"), ...rows(advanced));
      details.open = advanced.some((key) => key in object);
      children.push(details);
    }
    if (kind === "register" && Array.isArray(object.fields)) {
      children.push(this.bitMap(object));
    }
    if (kind === "field") {
      children.push(this.enumTable(object));
    }
    this.form.replaceChildren(...children);
  }

  private heading(kind: NodeKind, object: JsonObject): HTMLElement {
    const title = kind === "bus" ? "Bus" : `${labelOf(kind)} ${String(object.name)}`;
    const heading = element("div", { class: "bust-editor-heading" }, element("h3", {}, title));
    const placed = kind === "register" ? this.accepted!.layout[String(object.name)] : undefined;
    if (placed) {
      const bus = this.accepted!.data.bus as JsonObject;
      const digits = Math.ceil(Number(bus.addr_width) / 4) || 4;
      heading.append(element("p", {}, `At ${hex(placed.address, digits)}, ${placed.width} bits wide`));
    }
    return heading;
  }

  // Keys that do not apply to the object's type stay out of the form.
  private isShown(kind: NodeKind, key: string, object: JsonObject): boolean {
    if (["register", "fields", "enums", "$schema"].includes(key)) {
      return false;
    }
    if (key === "width" && (kind === "register" || kind === "field")) {
      return object.type === "vector" || "width" in object;
    }
    if (kind === "register" && object.type === "fields") {
      return !(ACCESS_KEYS.has(key) || key === "reset") || key in object;
    }
    return true;
  }

  private row(kind: NodeKind, object: JsonObject, key: string, property: JsonSchema, required: string[]): HTMLElement {
    const inputId = `${this.id}-${key}`;
    const input = this.input(key, property, object[key], required.includes(key), inputId);
    const commit = () => {
      this.editedKey = key;
      const value = this.readInput(input, key, property, required.includes(key));
      this.apply(this.operationsFor(kind, object, key, value));
    };
    input.addEventListener("change", commit);
    const row = element("div", { class: "bust-editor-row", "data-key": key });
    const label = element("label", { for: inputId }, labelOf(key));
    if (input instanceof HTMLInputElement && input.type === "checkbox") {
      row.classList.add("bust-editor-check");
      row.append(input, label);
    } else {
      row.append(label, input);
    }
    if (property.description) {
      const help = element("p", { class: "bust-editor-help", id: `${inputId}-help` }, property.description);
      input.setAttribute("aria-describedby", help.id);
      row.append(help);
    }
    return row;
  }

  private operationsFor(kind: NodeKind, object: JsonObject, key: string, value: JsonValue | undefined): Operation[] {
    if (key === "type" && kind === "register") {
      return setRegisterType(object, this.selected, value as string | undefined);
    }
    if (key === "type" && kind === "field") {
      return setFieldType(object, this.selected, value as string | undefined);
    }
    return setKey(object, this.selected, key, value);
  }

  private input(
    key: string,
    property: JsonSchema,
    value: JsonValue | undefined,
    isRequired: boolean,
    id: string,
  ): HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement {
    switch (inputKindOf(key, property)) {
      case "choice": {
        const select = element("select", { id });
        if (!isRequired || value === undefined) {
          const fallback = property.default === undefined ? "Not set" : `Default (${String(property.default)})`;
          select.append(element("option", { value: "" }, fallback));
        }
        select.append(...property.enum!.map((choice) => element("option", { value: choice }, choice)));
        select.value = value === undefined ? "" : String(value).toLowerCase();
        return select;
      }
      case "either": {
        const select = element(
          "select",
          { id },
          element("option", { value: "" }, placeholderOf(property) || "Not set"),
          element("option", { value: "true" }, "Yes"),
          element("option", { value: "false" }, "No"),
        );
        select.value = value === undefined || value === null ? "" : String(value);
        return select;
      }
      case "flag": {
        const checkbox = element("input", { id, type: "checkbox" });
        checkbox.checked = value === true;
        return checkbox;
      }
      case "longtext": {
        const textarea = element("textarea", { id, rows: "3" });
        textarea.value = value === undefined ? "" : String(value);
        return textarea;
      }
      default: {
        const text = element("input", { id, type: "text", spellcheck: "false", autocomplete: "off" });
        text.value = value === undefined || value === null ? "" : String(value);
        text.placeholder = placeholderOf(property);
        return text;
      }
    }
  }

  private readInput(
    input: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement,
    key: string,
    property: JsonSchema,
    isRequired: boolean,
  ): JsonValue | undefined {
    switch (inputKindOf(key, property)) {
      case "flag":
        return (input as HTMLInputElement).checked ? true : undefined;
      case "either":
        return input.value === "" ? undefined : input.value === "true";
      case "number":
        return parseNumber(input.value) ?? (isRequired ? "" : undefined);
      default:
        return input.value === "" && !isRequired ? undefined : input.value;
    }
  }

  // Shows each problem under the input of the value it is about, when that
  // value is in the form.
  private markProblemsInForm(): void {
    for (const row of this.form.querySelectorAll<HTMLElement>(".bust-editor-row")) {
      row.classList.remove("bust-editor-invalid");
      row.querySelector(".bust-editor-problem")?.remove();
      const path = [...this.selected, row.dataset.key!];
      const problems = this.problems.filter(
        (problem) =>
          startsWith(problem.path, path) || (problem.path.length === 0 && row.dataset.key === this.editedKey),
      );
      if (problems.length > 0) {
        row.classList.add("bust-editor-invalid");
        row.append(element("p", { class: "bust-editor-problem" }, problems.map((problem) => problem.message).join(" ")));
      }
    }
  }

  // The register's bits from the highest down, each field where bust put it.
  private bitMap(register: JsonObject): HTMLElement {
    const placed = this.accepted!.layout[String(register.name)];
    const width = Math.max(placed?.width ?? 0, Number((this.accepted!.data.bus as JsonObject).data_width) || 0);
    const map = element("div", { class: "bust-editor-bits", role: "group", "aria-label": "Fields by bit" });
    map.style.setProperty("--bust-editor-bit-count", String(width));
    const fields = (register.fields as JsonObject[]).map((field, index) => ({ field, index, span: placed?.fields[String(field.name)] }));
    for (const { field, index, span } of fields) {
      if (!span) {
        continue;
      }
      const cell = element(
        "button",
        { type: "button", title: `${String(field.name)} ${bits(span[0], span[1])}` },
        element("span", {}, String(field.name)),
        element("small", {}, bits(span[0], span[1])),
      );
      cell.style.gridColumn = `${width - span[1]} / ${width - span[0] + 1}`;
      cell.addEventListener("click", () => this.select([...this.selected, "fields", index]));
      map.append(cell);
    }
    return element("div", { class: "bust-editor-row" }, element("span", { class: "bust-editor-label" }, "Fields"), map);
  }

  private enumTable(field: JsonObject): HTMLElement {
    const enums = (field.enums as JsonObject[] | undefined) ?? [];
    const listPath = [...this.selected, "enums"];
    const cell = (index: number, key: "name" | "value") => {
      const input = element("input", { type: "text", spellcheck: "false", "aria-label": `${labelOf(key)} ${index + 1}` });
      input.value = String(enums[index][key]);
      input.addEventListener("change", () => {
        const value = key === "value" ? (parseNumber(input.value) ?? "") : input.value;
        this.apply(setKey(enums[index], [...listPath, index], key, value));
      });
      return element("td", {}, input);
    };
    const remove = (index: number) => {
      const button = element("button", { type: "button", "aria-label": `Remove value ${index + 1}` }, "Remove");
      button.addEventListener("click", () =>
        this.apply(enums.length === 1 ? setKey(field, this.selected, "enums", undefined) : removeAt(listPath, index)),
      );
      return element("td", {}, button);
    };
    const add = element("button", { type: "button" }, "Add value");
    add.addEventListener("click", () => {
      const name = uniqueName("VALUE", enums.map((value) => String(value.name)));
      const values = enums.map((value) => Number(parseNumber(String(value.value)))).filter(Number.isFinite);
      const value = { name, value: values.length > 0 ? Math.max(...values) + 1 : 0 };
      this.apply(enums.length === 0 ? setKey(field, this.selected, "enums", [value]) : insertAt(listPath, enums.length, value));
    });
    const table = element(
      "table",
      { class: "bust-editor-enums" },
      element("thead", {}, element("tr", {}, element("th", {}, "Name"), element("th", {}, "Value"), element("th", {}))),
      element("tbody", {}, ...enums.map((_, index) => element("tr", {}, cell(index, "name"), cell(index, "value"), remove(index)))),
    );
    return element(
      "div",
      { class: "bust-editor-row", "data-key": "enums" },
      element("span", { class: "bust-editor-label" }, "Named values"),
      ...(enums.length > 0 ? [table] : []),
      add,
    );
  }

  private addRegister(): Promise<EditorState> {
    const registers = (this.accepted!.data.module as JsonObject).register as JsonObject[];
    const kind = this.selectedKind();
    const index = kind === "register" || kind === "field" ? (this.selected[2] as number) + 1 : registers.length;
    const register: JsonObject = { name: uniqueName("reg", registers.map((other) => String(other.name))) };
    // Without an address of its own, a register put before one with an
    // address could take that address.
    if (registers[index] && "address" in registers[index]) {
      register.address = "0x" + this.accepted!.nextAddress.toString(16).toUpperCase();
    }
    return this.apply(insertAt(REGISTERS, index, register), [...REGISTERS, index]);
  }

  private addField(): Promise<EditorState> {
    const registerPath = this.selected.slice(0, 3);
    const register = valueAt(this.accepted!.data, registerPath) as JsonObject;
    const fields = (register.fields as JsonObject[] | undefined) ?? [];
    const name = uniqueName("field", fields.map((field) => String(field.name)));
    if (fields.length === 0) {
      const operations = setRegisterType(register, registerPath, "fields");
      return this.apply(operations, [...registerPath, "fields", 0]);
    }
    const index = this.selectedKind() === "field" ? (this.selected[4] as number) + 1 : fields.length;
    return this.apply(insertAt([...registerPath, "fields"], index, { name, type: "bit" }), [...registerPath, "fields", index]);
  }

  private moveSelected(step: number): Promise<EditorState> {
    const listPath = this.selected.slice(0, -1);
    const from = this.selected[this.selected.length - 1] as number;
    const list = valueAt(this.accepted!.data, listPath) as JsonValue[];
    return this.apply(move(listPath, list, from, from + step), [...listPath, from + step]);
  }

  private removeSelected(): Promise<EditorState> {
    const listPath = this.selected.slice(0, -1);
    const index = this.selected[this.selected.length - 1] as number;
    return this.apply(removeAt(listPath, index));
  }

  private onKey(event: KeyboardEvent): void {
    const target = event.target as HTMLElement;
    if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "z" || target.matches("input, textarea")) {
      return;
    }
    event.preventDefault();
    if (event.shiftKey) {
      this.redo();
    } else {
      this.undo();
    }
  }
}
