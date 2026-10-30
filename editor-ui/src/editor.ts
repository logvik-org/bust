import { bitDiagram } from "./diagram.js";
import { bitRange, element, hex } from "./dom.js";
import { FormDialog, type Draft, type FormSection } from "./form.js";
import { PopupMenu, type MenuItem } from "./menu.js";
import { editOperations, insertAt, move, newObject, removeAt, setRegisterType, uniqueName } from "./operations.js";
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
import { ADVANCED_KEYS, definitionOf, labelOf, placeholderOf, type NodeKind } from "./schema.js";

export type EditorOptions = {
  // Called with every register map bust accepts, after each change.
  onChange?: (state: AcceptedState) => void;
};

const REGISTERS: ValuePath = ["module", "register"];

// What the keys pane shows: the selected register, or one of its fields.
type Subject = "register" | "field";

const SHORTCUTS = {
  edit: "Enter",
  addRegister: "A",
  addField: "F",
  remove: "Del",
  module: "M",
  menu: "Shift+F10",
};

// The register map as bust's console editor shows it: the registers, the
// fields of the selected one with its bit diagram, and the keys of the
// register or field in focus. Changes are made in dialogs and from pop-up
// menus on each register and field, and every one goes to bust as JSON
// Patch. A change bust rejects keeps its dialog open with bust's problems
// next to the values they are about, so the editor only holds register maps
// bust accepts.
export class RegisterMapEditor {
  private schema?: JsonSchema;
  private accepted?: AcceptedState;
  private registerIndex = 0;
  private fieldIndex = 0;
  private subject: Subject = "register";
  private queue: Promise<unknown> = Promise.resolve();
  private readonly toolbar = element("div", { class: "bust-editor-toolbar", role: "toolbar", "aria-label": "Register map" });
  private readonly summary = element("div", { class: "bust-editor-summary" });
  private readonly messages = element("div", { class: "bust-editor-messages", role: "status", "aria-live": "polite" });
  private readonly registersPane = element("section", { class: "bust-editor-pane bust-editor-registers" });
  private readonly detailPane = element("section", { class: "bust-editor-pane bust-editor-detail" });
  private readonly keysPane = element("section", { class: "bust-editor-pane bust-editor-keys" });
  private readonly menu: PopupMenu;
  private readonly dialog: FormDialog;

  constructor(
    container: HTMLElement,
    private readonly bridge: BustBridge,
    private readonly options: EditorOptions = {},
  ) {
    container.classList.add("bust-editor");
    container.replaceChildren(
      element("div", { class: "bust-editor-head" }, this.summary, this.toolbar),
      this.messages,
      element(
        "div",
        { class: "bust-editor-body" },
        element("div", { class: "bust-editor-main" }, this.registersPane, this.detailPane),
        this.keysPane,
      ),
    );
    this.menu = new PopupMenu(container);
    this.dialog = new FormDialog(container);
    container.addEventListener("keydown", (event) => this.onKey(event));
  }

  get state(): AcceptedState | undefined {
    return this.accepted;
  }

  // Starts editing the register map in `text`. If bust rejects it, the
  // editor keeps what it had and the state lists bust's problems.
  open(text: string): Promise<EditorState> {
    return this.run(() => this.bridge.call("open", { text }), () => this.reset());
  }

  create(bus: JsonObject, module: JsonObject): Promise<EditorState> {
    return this.run(() => this.bridge.call("new", { bus, module }), () => this.reset());
  }

  apply(operations: Operation[], onAccepted?: () => void): Promise<EditorState> {
    return this.run(() => this.bridge.call("apply", { operations }), onAccepted);
  }

  undo(): Promise<EditorState> {
    return this.run(() => this.bridge.call("undo", {}));
  }

  redo(): Promise<EditorState> {
    return this.run(() => this.bridge.call("redo", {}));
  }

  // Resolves when every change made so far has come back from bust.
  async idle(): Promise<void> {
    await this.queue;
  }

  // One request at a time, so that quick changes reach bust in order.
  private run(request: () => Promise<EditorState>, onAccepted?: () => void): Promise<EditorState> {
    const result = this.queue.then(async () => {
      this.schema ??= await this.bridge.call("schema", {});
      const state = await request();
      if (state.accepted) {
        this.accepted = state;
        onAccepted?.();
        this.render();
        this.showProblems([]);
        this.options.onChange?.(state);
      } else {
        this.showProblems(state.problems);
      }
      return state;
    });
    this.queue = result.catch(() => undefined);
    return result;
  }

  // Makes a change from a dialog: problems keep the dialog open.
  private async applyFromDialog(operations: Operation[], onAccepted?: () => void): Promise<Problem[] | undefined> {
    if (operations.length === 0) {
      return undefined;
    }
    const state = await this.apply(operations, onAccepted);
    if (state.accepted) {
      return undefined;
    }
    this.showProblems([]);
    return state.problems;
  }

  // The register map as bust read it.

  private get data(): JsonObject {
    return this.accepted!.data;
  }

  private get registers(): JsonObject[] {
    return (this.data.module as JsonObject).register as JsonObject[];
  }

  private get register(): JsonObject | undefined {
    return this.registers[this.registerIndex];
  }

  private get fields(): JsonObject[] {
    return (this.register?.fields as JsonObject[] | undefined) ?? [];
  }

  private get addressDigits(): number {
    return Math.ceil(Number((this.data.bus as JsonObject).addr_width) / 4) || 4;
  }

  private registerPath(index = this.registerIndex): ValuePath {
    return [...REGISTERS, index];
  }

  private fieldPath(index = this.fieldIndex): ValuePath {
    return [...this.registerPath(), "fields", index];
  }

  // Showing it.

  private render(): void {
    this.registerIndex = Math.min(this.registerIndex, Math.max(this.registers.length - 1, 0));
    this.fieldIndex = Math.min(this.fieldIndex, Math.max(this.fields.length - 1, 0));
    if (this.fields.length === 0) {
      this.subject = "register";
    }
    this.renderToolbar();
    this.renderSummary();
    this.renderRegisters();
    this.renderDetail();
    this.renderKeys();
  }

  private button(label: string, action: () => void, options: { shortcut?: string; isEnabled?: boolean; className?: string } = {}): HTMLButtonElement {
    const created = element("button", { type: "button" }, label);
    created.disabled = options.isEnabled === false;
    if (options.shortcut) {
      created.title = `${label} (${options.shortcut})`;
    }
    if (options.className) {
      created.className = options.className;
    }
    created.addEventListener("click", action);
    return created;
  }

  private renderToolbar(): void {
    const state = this.accepted!;
    this.toolbar.replaceChildren(
      element(
        "div",
        { class: "bust-editor-group" },
        this.button("Undo", () => this.undo(), { isEnabled: state.canUndo, shortcut: "Ctrl+Z" }),
        this.button("Redo", () => this.redo(), { isEnabled: state.canRedo, shortcut: "Ctrl+Shift+Z" }),
      ),
      this.button("Add register", () => this.addRegister(this.registers.length), { shortcut: SHORTCUTS.addRegister }),
    );
  }

  private renderSummary(): void {
    const module = this.data.module as JsonObject;
    const bus = this.data.bus as JsonObject;
    const facts = [`${String(bus.type)} bus`, `${String(bus.addr_width)}-bit addresses`, `${String(bus.data_width)}-bit data`];
    if (module.version) {
      facts.push(`version ${String(module.version)}`);
    }
    const name = this.button(String(module.name), () => this.editModule(), { className: "bust-editor-module-name" });
    name.title = `Module and bus (${SHORTCUTS.module})`;
    this.summary.replaceChildren(name, element("span", {}, facts.join(" · ")));
    if (module.description) {
      this.summary.append(element("p", {}, String(module.description)));
    }
  }

  private renderRegisters(): void {
    const { layout } = this.accepted!;
    const rows = this.registers.map((register, index) => {
      const placed = layout[String(register.name)];
      return this.tableRow(
        [
          placed ? hex(placed.address, this.addressDigits) : "",
          String(register.name),
          placed?.type ?? String(register.type ?? ""),
          placed ? String(placed.width) : "",
          placed?.access ?? "",
          placed?.reset ?? "",
          String(register.description ?? ""),
        ],
        index === this.registerIndex,
        () => this.selectRegister(index),
        () => this.editRegister(),
        (x, y, anchor) => this.registerMenu(x, y, anchor),
      );
    });
    const empty = element("p", { class: "bust-editor-empty" }, "No registers yet. ", this.button("Add register", () => this.addRegister(0)));
    this.registersPane.replaceChildren(
      element("h3", {}, "Registers"),
      rows.length > 0 ? this.table(["Address", "Name", "Type", "Width", "SW/HW", "Reset", "Description"], rows, "Registers") : empty,
    );
  }

  private renderDetail(): void {
    const register = this.register;
    if (!register) {
      this.detailPane.replaceChildren();
      return;
    }
    const placed = this.accepted!.layout[String(register.name)];
    const heading = element(
      "div",
      { class: "bust-editor-pane-head" },
      element("h3", {}, `${register.type === "fields" ? "Fields" : "Bits"} of ${String(register.name)}`),
      this.button("Add field", () => this.addField(this.fields.length), { shortcut: SHORTCUTS.addField }),
    );
    const children: Node[] = [heading];
    if (placed) {
      const selected = this.subject === "field" ? String(this.fields[this.fieldIndex]?.name) : undefined;
      const onSelect = register.type === "fields" ? (name: string) => this.selectField(this.fields.findIndex((field) => field.name === name)) : undefined;
      children.push(bitDiagram(placed.segments, selected, onSelect));
    }
    if (this.fields.length > 0) {
      const rows = this.fields.map((field, index) => {
        const fieldLayout = placed?.fields[String(field.name)];
        return this.tableRow(
          [
            fieldLayout ? bitRange(fieldLayout.low, fieldLayout.high) : "",
            String(field.name),
            String(field.type),
            fieldLayout?.access ?? "",
            fieldLayout?.reset ?? "",
            String(field.description ?? ""),
          ],
          this.subject === "field" && index === this.fieldIndex,
          () => this.selectField(index),
          () => this.editField(),
          (x, y, anchor) => this.fieldMenu(x, y, anchor),
        );
      });
      children.push(this.table(["Bits", "Name", "Type", "SW/HW", "Reset", "Description"], rows, `Fields of ${String(register.name)}`));
    } else {
      children.push(element("p", { class: "bust-editor-empty" }, "A register of type fields holds named fields. Add one to turn this register into one."));
    }
    this.detailPane.replaceChildren(...children);
  }

  private table(headings: string[], rows: HTMLTableRowElement[], label: string): HTMLElement {
    return element(
      "div",
      { class: "bust-editor-table-wrap" },
      element(
        "table",
        { class: "bust-editor-table", "aria-label": label },
        element("thead", {}, element("tr", {}, ...headings.map((heading) => element("th", {}, heading)), element("th", { class: "bust-editor-actions" }, element("span", { class: "bust-editor-hidden" }, "Actions")))),
        element("tbody", {}, ...rows),
      ),
    );
  }

  private tableRow(
    cells: string[],
    isSelected: boolean,
    select: () => void,
    edit: () => void,
    openMenu: (x: number, y: number, anchor?: HTMLElement) => void,
  ): HTMLTableRowElement {
    const more = element("button", { type: "button", class: "bust-editor-more", "aria-label": "Actions", "aria-haspopup": "menu", title: `Actions (right-click or ${SHORTCUTS.menu})` }, "⋯");
    more.addEventListener("click", (event) => {
      event.stopPropagation();
      select();
      const box = more.getBoundingClientRect();
      openMenu(box.left, box.bottom + 2, more);
    });
    const row = element(
      "tr",
      { tabindex: isSelected ? "0" : "-1" },
      ...cells.map((cell, index) => element("td", index === 1 ? { class: "bust-editor-name" } : {}, cell)),
      element("td", { class: "bust-editor-actions" }, more),
    );
    if (isSelected) {
      row.setAttribute("aria-selected", "true");
    }
    row.addEventListener("click", select);
    row.addEventListener("dblclick", () => {
      select();
      edit();
    });
    row.addEventListener("contextmenu", (event) => {
      event.preventDefault();
      select();
      openMenu(event.clientX, event.clientY);
    });
    return row;
  }

  // The keys of the register or field in focus, with the values bust uses
  // for those the file leaves out. A click on one changes it.
  private renderKeys(): void {
    const kind: NodeKind = this.subject;
    const object = kind === "field" ? this.fields[this.fieldIndex] : this.register;
    if (!object) {
      this.keysPane.replaceChildren(element("h3", {}, "Keys"), element("p", { class: "bust-editor-empty" }, "Add a register to see its keys."));
      return;
    }
    const definition = definitionOf(this.schema!, kind);
    const owner = kind === "field" ? `Field ${String(object.name)} of ${String(this.register!.name)}` : `Register ${String(object.name)}`;
    const list = element("dl", { class: "bust-editor-key-list" });
    for (const [key, property] of Object.entries(definition.properties ?? {})) {
      // The rarely used access keys show only when set, as the dialog keeps
      // them under "More access options".
      if (["fields", "$schema"].includes(key) || (ADVANCED_KEYS.has(key) && object[key] === undefined)) {
        continue;
      }
      const value = this.shownValue(kind, object, key, property);
      const button = this.button(labelOf(key), () => (kind === "field" ? this.editField(key) : this.editRegister(key)));
      button.title = property.description ?? "";
      const valueElement = element("dd", {}, value.text);
      if (!value.isSet) {
        valueElement.classList.add("bust-editor-unset");
      }
      list.append(element("div", { "data-key": key }, element("dt", {}, button), valueElement));
    }
    const edit = this.button("Edit", () => (kind === "field" ? this.editField() : this.editRegister()), { shortcut: SHORTCUTS.edit });
    this.keysPane.replaceChildren(element("div", { class: "bust-editor-pane-head" }, element("h3", {}, owner), edit), list);
  }

  private shownValue(kind: NodeKind, object: JsonObject, key: string, property: JsonSchema): { text: string; isSet: boolean } {
    const value = object[key];
    if (key === "enums") {
      const entries = Array.isArray(value) ? (value as JsonObject[]) : [];
      const text = entries.map((entry) => `${String(entry.name)} = ${String(entry.value)}`).join(", ");
      return { text: text || "none", isSet: entries.length > 0 };
    }
    if (value !== undefined && value !== null) {
      return { text: String(value), isSet: true };
    }
    const placed = this.accepted!.layout[String(this.register!.name)];
    const known: Record<string, string | undefined> = {
      address: placed ? hex(placed.address, this.addressDigits) : undefined,
      width: placed && kind === "register" ? String(placed.width) : undefined,
      position: kind === "field" ? String(placed?.fields[String(object.name)]?.low ?? "") : undefined,
    };
    const fallback = known[key] ?? (property.default !== undefined ? String(property.default) : placeholderOf(property).replace(/^Default: /, ""));
    return { text: fallback ? `${fallback} (not set)` : "not set", isSet: false };
  }

  private showProblems(problems: Problem[]): void {
    if (problems.length === 0) {
      this.messages.replaceChildren(...this.warningItems());
      return;
    }
    this.messages.replaceChildren(
      element("p", { class: "bust-editor-rejected" }, "bust did not make this change:"),
      element(
        "ul",
        { class: "bust-editor-problems" },
        ...problems.map((problem) => element("li", {}, problem.location ? `${problem.location}: ${problem.message}` : problem.message)),
      ),
      ...this.warningItems(),
    );
  }

  private warningItems(): HTMLElement[] {
    const warnings = this.accepted?.warnings ?? [];
    return warnings.length === 0
      ? []
      : [element("ul", { class: "bust-editor-warnings" }, ...warnings.map((warning) => element("li", {}, `Ignored: ${warning}`)))];
  }

  // Selection.

  private reset(): void {
    this.registerIndex = 0;
    this.fieldIndex = 0;
    this.subject = "register";
  }

  private selectRegister(index: number): void {
    const isNew = index !== this.registerIndex;
    this.registerIndex = index;
    this.subject = "register";
    if (isNew) {
      this.fieldIndex = 0;
    }
    if (this.accepted) {
      this.render();
      this.focusSelectedRow(this.registersPane);
    }
  }

  private selectField(index: number): void {
    if (index < 0) {
      return;
    }
    this.fieldIndex = index;
    this.subject = "field";
    this.render();
    this.focusSelectedRow(this.detailPane);
  }

  private focusSelectedRow(pane: HTMLElement): void {
    pane.querySelector<HTMLElement>("tr[aria-selected='true']")?.focus({ preventScroll: false });
  }

  // Menus.

  private registerMenu(x: number, y: number, anchor?: HTMLElement): void {
    const index = this.registerIndex;
    const items: MenuItem[] = [
      { label: "Edit register…", shortcut: SHORTCUTS.edit, action: () => this.editRegister() },
      { label: "Add field…", shortcut: SHORTCUTS.addField, action: () => this.addField(this.fields.length) },
      "separator",
      { label: "Insert register above…", action: () => this.addRegister(index) },
      { label: "Insert register below…", shortcut: SHORTCUTS.addRegister, action: () => this.addRegister(index + 1) },
      { label: "Duplicate", action: () => this.duplicate(REGISTERS, this.registers, index, "register") },
      "separator",
      { label: "Move up", isDisabled: index === 0, action: () => this.moveSelected(REGISTERS, this.registers, index, -1, "register") },
      { label: "Move down", isDisabled: index >= this.registers.length - 1, action: () => this.moveSelected(REGISTERS, this.registers, index, 1, "register") },
      "separator",
      { label: "Remove register", shortcut: SHORTCUTS.remove, isDangerous: true, action: () => this.apply(removeAt(REGISTERS, index)) },
    ];
    this.menu.openAt(x, y, `Register ${String(this.register!.name)}`, items, anchor ?? this.focusTarget());
  }

  private fieldMenu(x: number, y: number, anchor?: HTMLElement): void {
    const index = this.fieldIndex;
    const listPath = [...this.registerPath(), "fields"];
    const items: MenuItem[] = [
      { label: "Edit field…", shortcut: SHORTCUTS.edit, action: () => this.editField() },
      { label: "Named values…", action: () => this.editField("enums") },
      "separator",
      { label: "Insert field above…", action: () => this.addField(index) },
      { label: "Insert field below…", shortcut: SHORTCUTS.addField, action: () => this.addField(index + 1) },
      { label: "Duplicate", action: () => this.duplicate(listPath, this.fields, index, "field") },
      "separator",
      { label: "Move up", isDisabled: index === 0, action: () => this.moveSelected(listPath, this.fields, index, -1, "field") },
      { label: "Move down", isDisabled: index >= this.fields.length - 1, action: () => this.moveSelected(listPath, this.fields, index, 1, "field") },
      "separator",
      { label: "Remove field", shortcut: SHORTCUTS.remove, isDangerous: true, action: () => this.apply(removeAt(listPath, index)) },
    ];
    this.menu.openAt(x, y, `Field ${String(this.fields[index].name)}`, items, anchor ?? this.focusTarget());
  }

  private focusTarget(): HTMLElement | undefined {
    const pane = this.subject === "field" ? this.detailPane : this.registersPane;
    return pane.querySelector<HTMLElement>("tr[aria-selected='true']") ?? undefined;
  }

  private openMenuForSelection(): void {
    const row = this.focusTarget();
    if (!row) {
      return;
    }
    const box = row.getBoundingClientRect();
    if (this.subject === "field") {
      this.fieldMenu(box.left + 24, box.bottom, row);
    } else {
      this.registerMenu(box.left + 24, box.bottom, row);
    }
  }

  // Dialogs.

  private section(kind: NodeKind, values: JsonObject, path: ValuePath, heading?: string): FormSection {
    return { kind, heading, definition: definitionOf(this.schema!, kind), values, path };
  }

  private formKeys(kind: NodeKind): string[] {
    return Object.keys(definitionOf(this.schema!, kind).properties ?? {}).filter((key) => !["register", "fields", "$schema"].includes(key));
  }

  private editModule(): void {
    const bus = this.data.bus as JsonObject;
    const module = this.data.module as JsonObject;
    this.dialog.open({
      title: "Module and bus",
      submitLabel: "Save",
      sections: [this.section("module", module, ["module"], "Module"), this.section("bus", bus, ["bus"], "Bus")],
      submit: ([moduleDraft, busDraft]) =>
        this.applyFromDialog([
          ...editOperations("module", module, ["module"], moduleDraft, this.formKeys("module")),
          ...editOperations("bus", bus, ["bus"], busDraft, this.formKeys("bus")),
        ]),
    });
  }

  private editRegister(focusKey?: string): void {
    const register = this.register;
    if (!register) {
      return;
    }
    const path = this.registerPath();
    this.dialog.open({
      title: `Register ${String(register.name)}`,
      submitLabel: "Save",
      focusKey,
      sections: [this.section("register", register, path)],
      submit: ([draft]) => this.applyFromDialog(editOperations("register", register, path, draft, this.formKeys("register"))),
    });
  }

  private editField(focusKey?: string): void {
    const field = this.fields[this.fieldIndex];
    if (!field) {
      return;
    }
    const path = this.fieldPath();
    this.dialog.open({
      title: `Field ${String(field.name)} of ${String(this.register!.name)}`,
      submitLabel: "Save",
      focusKey,
      sections: [this.section("field", field, path)],
      submit: ([draft]) => this.applyFromDialog(editOperations("field", field, path, draft, this.formKeys("field"))),
    });
  }

  private addRegister(index: number): void {
    const values: JsonObject = { name: uniqueName("reg", this.registers.map((register) => String(register.name))) };
    const address = this.addressBefore(index);
    if (address) {
      values.address = address;
    }
    this.dialog.open({
      title: "Add register",
      submitLabel: "Add",
      sections: [this.section("register", values, this.registerPath(index))],
      submit: ([draft]) =>
        this.applyFromDialog(insertAt(REGISTERS, index, newObject("register", draft)), () => this.selectRegister(index)),
    });
  }

  // Without an address of its own, a register put before one with an
  // address could take that address.
  private addressBefore(index: number): string | undefined {
    const next = this.registers[index];
    return next && "address" in next ? "0x" + this.accepted!.nextAddress.toString(16).toUpperCase() : undefined;
  }

  private addField(index: number): void {
    const register = this.register;
    if (!register) {
      return;
    }
    const values: JsonObject = { name: uniqueName("field", this.fields.map((field) => String(field.name))), type: "bit" };
    const registerPath = this.registerPath();
    const listPath = [...registerPath, "fields"];
    this.dialog.open({
      title: `Add field to ${String(register.name)}`,
      submitLabel: "Add",
      sections: [this.section("field", values, [...listPath, index])],
      submit: ([draft]) => this.applyFromDialog(this.addFieldOperations(register, index, draft), () => this.selectField(index)),
    });
  }

  // The first field makes the register a fields register, which leaves no
  // place for the keys only a register of bits has.
  private addFieldOperations(register: JsonObject, index: number, draft: Draft): Operation[] {
    const registerPath = this.registerPath();
    const field = newObject("field", draft);
    if (this.fields.length > 0) {
      return insertAt([...registerPath, "fields"], index, field);
    }
    return setRegisterType(register, registerPath, "fields").map((operation) =>
      operation.op === "add" && operation.path.endsWith("/fields") ? { ...operation, value: [field] } : operation,
    );
  }

  private duplicate(listPath: ValuePath, list: JsonObject[], index: number, kind: "register" | "field"): Promise<EditorState> {
    const copy: JsonObject = structuredClone(list[index]);
    copy.name = uniqueName(`${String(copy.name)}_copy`, list.map((item) => String(item.name)));
    if (kind === "register") {
      delete copy.address;
      const address = this.addressBefore(index + 1);
      if (address) {
        copy.address = address;
      }
    } else {
      delete copy.position;
    }
    const select = () => (kind === "register" ? this.selectRegister(index + 1) : this.selectField(index + 1));
    return this.apply(insertAt(listPath, index + 1, copy), select);
  }

  private moveSelected(listPath: ValuePath, list: JsonValue[], index: number, step: number, kind: "register" | "field"): Promise<EditorState> {
    const select = () => (kind === "register" ? this.selectRegister(index + step) : this.selectField(index + step));
    return this.apply(move(listPath, list, index, index + step), select);
  }

  private removeSelected(): void {
    if (this.subject === "field" && this.fields.length > 0) {
      this.apply(removeAt([...this.registerPath(), "fields"], this.fieldIndex));
    } else if (this.register) {
      this.apply(removeAt(REGISTERS, this.registerIndex));
    }
  }

  // Keys, as in the console editor.

  private onKey(event: KeyboardEvent): void {
    const target = event.target as HTMLElement;
    if (!this.accepted || this.dialog.isOpen || this.menu.isOpen || target.matches("input, textarea, select")) {
      return;
    }
    const key = event.key;
    if ((event.ctrlKey || event.metaKey) && key.toLowerCase() === "z") {
      event.preventDefault();
      if (event.shiftKey) {
        this.redo();
      } else {
        this.undo();
      }
      return;
    }
    if (event.ctrlKey || event.metaKey || event.altKey) {
      return;
    }
    const isRow = target.matches("tr");
    const actions: Record<string, () => void> = {
      a: () => this.addRegister(this.register ? this.registerIndex + 1 : 0),
      f: () => this.addField(this.subject === "field" ? this.fieldIndex + 1 : this.fields.length),
      m: () => this.editModule(),
      Delete: () => this.removeSelected(),
      ContextMenu: () => this.openMenuForSelection(),
    };
    if (isRow) {
      Object.assign(actions, {
        Enter: () => (this.subject === "field" ? this.editField() : this.editRegister()),
        ArrowDown: () => this.step(1),
        ArrowUp: () => this.step(-1),
      });
    }
    const action = key === "F10" && event.shiftKey ? actions.ContextMenu : actions[key.length === 1 ? key.toLowerCase() : key];
    if (action) {
      event.preventDefault();
      action();
    }
  }

  private step(change: number): void {
    if (this.subject === "field") {
      const index = this.fieldIndex + change;
      if (index >= 0 && index < this.fields.length) {
        this.selectField(index);
      }
      return;
    }
    const index = this.registerIndex + change;
    if (index >= 0 && index < this.registers.length) {
      this.selectRegister(index);
    }
  }
}
