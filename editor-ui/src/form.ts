import { element } from "./dom.js";
import type { JsonObject, JsonSchema, JsonValue, Problem, ValuePath } from "./protocol.js";
import { ACCESS_KEYS, ADVANCED_KEYS, inputKindOf, labelOf, parseNumber, placeholderOf, type NodeKind } from "./schema.js";

type Input = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;

// The values a section of the form holds, by key. An undefined value means
// the key is left out of the register map.
export type Draft = Record<string, JsonValue | undefined>;

export type FormSection = {
  kind: NodeKind;
  heading?: string;
  definition: JsonSchema;
  values: JsonObject;
  // Where the object sits in the register map, to place bust's problems.
  path: ValuePath;
};

export type FormRequest = {
  title: string;
  submitLabel: string;
  sections: FormSection[];
  focusKey?: string;
  // Makes the change. Problems keep the dialog open and show next to the
  // values they are about.
  submit: (drafts: Draft[]) => Promise<Problem[] | undefined>;
};

type Row = { key: string; property: JsonSchema; isRequired: boolean; element: HTMLElement; read: () => JsonValue | undefined };

let nextFormId = 0;

// Keys that do not apply to an object's type stay out of the form.
export function isShown(kind: NodeKind, key: string, values: Draft): boolean {
  if (["register", "fields", "$schema"].includes(key)) {
    return false;
  }
  if (key === "enums") {
    return kind === "field";
  }
  if (key === "width" && (kind === "register" || kind === "field")) {
    return values.type === "vector";
  }
  if (kind === "register" && values.type === "fields") {
    return !(ACCESS_KEYS.has(key) || key === "reset") || values[key] !== undefined;
  }
  return true;
}

// A dialog with a form built from bust's JSON Schema, one section per object.
export class FormDialog {
  private readonly dialog = element("dialog", { class: "bust-editor-dialog" });
  private sectionRows: Row[][] = [];
  private request?: FormRequest;

  constructor(host: HTMLElement) {
    host.append(this.dialog);
    this.dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      this.close();
    });
  }

  get isOpen(): boolean {
    return this.dialog.open;
  }

  open(request: FormRequest): void {
    this.request = request;
    const id = `bust-editor-form-${nextFormId++}`;
    const form = element("form", { method: "dialog", "aria-labelledby": `${id}-title` });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      this.submit();
    });
    const cancel = element("button", { type: "button" }, "Cancel");
    cancel.addEventListener("click", () => this.close());
    this.sectionRows = request.sections.map((section) => this.rows(section, id));
    form.append(
      element("h2", { id: `${id}-title` }, request.title),
      element("div", { class: "bust-editor-dialog-problems", role: "alert" }),
      ...request.sections.flatMap((section, index) => this.sectionElements(section, this.sectionRows[index])),
      element(
        "div",
        { class: "bust-editor-dialog-buttons" },
        element("button", { type: "submit", class: "bust-editor-primary" }, request.submitLabel),
        cancel,
      ),
    );
    this.dialog.replaceChildren(form);
    this.updateVisibility();
    if (typeof this.dialog.showModal === "function") {
      this.dialog.showModal();
    } else {
      this.dialog.setAttribute("open", "");
    }
    const focused = this.sectionRows.flat().find((row) => row.key === request.focusKey) ?? this.sectionRows.flat()[0];
    focused?.element.querySelector<HTMLElement>("input, select, textarea")?.focus();
  }

  close(): void {
    if (typeof this.dialog.close === "function") {
      this.dialog.close();
    }
    this.dialog.removeAttribute("open");
    this.request = undefined;
  }

  private sectionElements(section: FormSection, rows: Row[]): Node[] {
    const plain = rows.filter((row) => !ADVANCED_KEYS.has(row.key)).map((row) => row.element);
    const advanced = rows.filter((row) => ADVANCED_KEYS.has(row.key));
    const nodes: Node[] = section.heading ? [element("h3", {}, section.heading), ...plain] : plain;
    if (advanced.length > 0) {
      const details = element("details", {}, element("summary", {}, "More access options"), ...advanced.map((row) => row.element));
      details.open = advanced.some((row) => section.values[row.key] !== undefined);
      nodes.push(details);
    }
    return nodes;
  }

  private rows(section: FormSection, formId: string): Row[] {
    const required = section.definition.required ?? [];
    return Object.entries(section.definition.properties!)
      .filter(([key]) => !["register", "fields", "$schema"].includes(key) && (key !== "enums" || section.kind === "field"))
      .map(([key, property]) => this.row(section, key, property, required.includes(key), `${formId}-${section.kind}-${key}`));
  }

  private row(section: FormSection, key: string, property: JsonSchema, isRequired: boolean, id: string): Row {
    const value = section.values[key];
    if (key === "enums") {
      return this.enumRow(value as JsonObject[] | undefined, property, id);
    }
    const input = inputFor(key, property, value, isRequired, id);
    const label = element("label", { for: id }, labelOf(key));
    const rowElement = element("div", { class: "bust-editor-row", "data-key": key });
    if (input instanceof HTMLInputElement && input.type === "checkbox") {
      rowElement.classList.add("bust-editor-check");
      rowElement.append(input, label);
    } else {
      rowElement.append(label, input);
    }
    if (property.description) {
      const help = element("p", { class: "bust-editor-help", id: `${id}-help` }, property.description);
      input.setAttribute("aria-describedby", help.id);
      rowElement.append(help);
    }
    if (key === "type") {
      input.addEventListener("change", () => this.updateVisibility());
    }
    return { key, property, isRequired, element: rowElement, read: () => readInput(input, key, property, isRequired) };
  }

  // The named values of a field: a small table of names and numbers.
  private enumRow(values: JsonObject[] | undefined, property: JsonSchema, id: string): Row {
    const body = element("tbody");
    const addRow = (name: string, value: string) => {
      const index = body.children.length + 1;
      const nameInput = element("input", { type: "text", spellcheck: "false", autocomplete: "off", "aria-label": `Name of value ${index}` });
      const valueInput = element("input", { type: "text", spellcheck: "false", autocomplete: "off", "aria-label": `Value ${index}` });
      nameInput.value = name;
      valueInput.value = value;
      const remove = element("button", { type: "button", "aria-label": `Remove value ${index}` }, "Remove");
      const row = element("tr", {}, element("td", {}, nameInput), element("td", {}, valueInput), element("td", {}, remove));
      remove.addEventListener("click", () => row.remove());
      body.append(row);
      return nameInput;
    };
    for (const value of values ?? []) {
      addRow(String(value.name), String(value.value));
    }
    const add = element("button", { type: "button" }, "Add value");
    add.addEventListener("click", () => {
      const numbers = [...body.querySelectorAll<HTMLInputElement>("td:nth-child(2) input")].map((input) => Number(parseNumber(input.value)));
      const next = numbers.filter(Number.isFinite).reduce((highest, number) => Math.max(highest, number + 1), 0);
      addRow(`VALUE${body.children.length}`, String(next)).focus();
    });
    const table = element(
      "table",
      { class: "bust-editor-enums", id },
      element("thead", {}, element("tr", {}, element("th", {}, "Name"), element("th", {}, "Value"), element("th", {}))),
      body,
    );
    const rowElement = element(
      "div",
      { class: "bust-editor-row bust-editor-wide", "data-key": "enums" },
      element("span", { class: "bust-editor-label" }, "Named values"),
      element("p", { class: "bust-editor-help" }, property.description ?? ""),
      table,
      add,
    );
    const read = (): JsonValue | undefined => {
      const rows = [...body.querySelectorAll("tr")].map((row) => {
        const [name, value] = row.querySelectorAll("input");
        return { name: name.value, value: parseNumber(value.value) ?? "" };
      });
      return rows.length > 0 ? rows : undefined;
    };
    return { key: "enums", property, isRequired: false, element: rowElement, read };
  }

  private drafts(): Draft[] {
    return this.sectionRows.map((rows) =>
      Object.fromEntries(rows.filter((row) => !row.element.hidden).map((row) => [row.key, row.read()])),
    );
  }

  private updateVisibility(): void {
    this.request?.sections.forEach((section, index) => {
      const rows = this.sectionRows[index];
      const values: Draft = { ...section.values, ...Object.fromEntries(rows.map((row) => [row.key, row.read()])) };
      for (const row of rows) {
        row.element.hidden = !isShown(section.kind, row.key, values);
      }
    });
  }

  private async submit(): Promise<void> {
    const request = this.request;
    if (!request) {
      return;
    }
    const problems = await request.submit(this.drafts());
    if (problems === undefined) {
      this.close();
      return;
    }
    this.showProblems(request, problems);
  }

  // Each problem goes under the value it is about. The ones bust gives
  // without a place, or for a value not in the form, go at the top.
  private showProblems(request: FormRequest, problems: Problem[]): void {
    const unplaced: Problem[] = [];
    for (const row of this.sectionRows.flat()) {
      row.element.classList.remove("bust-editor-invalid");
      row.element.querySelector(".bust-editor-problem")?.remove();
    }
    for (const problem of problems) {
      const row = request.sections
        .flatMap((section, index) => this.sectionRows[index].map((candidate) => ({ section, candidate })))
        .find(({ section, candidate }) => startsWith(problem.path, [...section.path, candidate.key]))?.candidate;
      if (!row || row.element.hidden) {
        unplaced.push(problem);
        continue;
      }
      row.element.classList.add("bust-editor-invalid");
      row.element.append(element("p", { class: "bust-editor-problem" }, problem.message));
    }
    const top = this.dialog.querySelector(".bust-editor-dialog-problems")!;
    top.replaceChildren(
      ...(unplaced.length > 0
        ? [element("ul", {}, ...unplaced.map((problem) => element("li", {}, problem.message)))]
        : []),
    );
    this.dialog.querySelector<HTMLElement>(".bust-editor-invalid input, .bust-editor-invalid select")?.focus();
  }
}

export function startsWith(path: ValuePath, prefix: ValuePath): boolean {
  return prefix.length <= path.length && prefix.every((token, index) => token === path[index]);
}

function inputFor(key: string, property: JsonSchema, value: JsonValue | undefined, isRequired: boolean, id: string): Input {
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

function readInput(input: Input, key: string, property: JsonSchema, isRequired: boolean): JsonValue | undefined {
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
