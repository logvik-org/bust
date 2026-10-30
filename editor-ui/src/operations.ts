import { pointer, type JsonObject, type JsonValue, type Operation, type ValuePath } from "./protocol.js";

// The operations that set `key` of the object at `path` to `value`, or take
// the key out when `value` is undefined.
export function setKey(object: JsonObject, path: ValuePath, key: string, value: JsonValue | undefined): Operation[] {
  const target = pointer([...path, key]);
  const isPresent = key in object;
  if (value === undefined) {
    return isPresent ? [{ op: "remove", path: target }] : [];
  }
  return [{ op: isPresent ? "replace" : "add", path: target, value }];
}

// Changing a register's type also adds or takes out the keys only some types
// have, so that the change does not leave a register bust rejects.
export function setRegisterType(
  register: JsonObject,
  path: ValuePath,
  type: string | undefined,
): Operation[] {
  const operations = setKey(register, path, "type", type);
  if (type === "fields" && !("fields" in register)) {
    operations.push(...setKey(register, path, "fields", [{ name: "field0", type: "bit" }]));
    for (const key of ["reset", "width"]) {
      operations.push(...setKey(register, path, key, undefined));
    }
  }
  if (type !== "fields") {
    operations.push(...setKey(register, path, "fields", undefined));
  }
  if (type !== "vector") {
    operations.push(...setKey(register, path, "width", undefined));
  }
  return operations;
}

// A field's type picks between bit and vector, and only a vector has a width.
export function setFieldType(field: JsonObject, path: ValuePath, type: string | undefined): Operation[] {
  const operations = setKey(field, path, "type", type);
  if (type !== "vector") {
    operations.push(...setKey(field, path, "width", undefined));
  }
  return operations;
}

export function insertAt(listPath: ValuePath, index: number, value: JsonValue): Operation[] {
  return [{ op: "add", path: pointer([...listPath, index]), value }];
}

export function removeAt(listPath: ValuePath, index: number): Operation[] {
  return [{ op: "remove", path: pointer([...listPath, index]) }];
}

export function move(listPath: ValuePath, list: JsonValue[], from: number, to: number): Operation[] {
  return [...removeAt(listPath, from), ...insertAt(listPath, to, list[from])];
}

export function uniqueName(prefix: string, taken: Iterable<string>): string {
  const names = new Set(taken);
  for (let number = 0; ; number++) {
    if (!names.has(`${prefix}${number}`)) {
      return `${prefix}${number}`;
    }
  }
}

function isSame(a: JsonValue | undefined, b: JsonValue | undefined): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

// The operations that turn `original` into what a form holds. Keys the form
// hides for the object's type are taken out.
export function editOperations(
  kind: "bus" | "module" | "register" | "field",
  original: JsonObject,
  path: ValuePath,
  draft: Record<string, JsonValue | undefined>,
  formKeys: string[],
): Operation[] {
  const operations: Operation[] = [];
  if ("type" in draft && !isSame(draft.type, original.type)) {
    const type = draft.type as string | undefined;
    if (kind === "register") {
      operations.push(...setRegisterType(original, path, type));
    } else if (kind === "field") {
      operations.push(...setFieldType(original, path, type));
    } else {
      operations.push(...setKey(original, path, "type", type));
    }
  }
  const touched = new Set(operations.map((operation) => operation.path));
  for (const key of formKeys) {
    const target = pointer([...path, key]);
    if (key === "type" || touched.has(target)) {
      continue;
    }
    const value = key in draft ? draft[key] : undefined;
    if (!isSame(value, original[key])) {
      operations.push(...setKey(original, path, key, value));
    }
  }
  return operations;
}

// A new register or field from what a form holds.
export function newObject(kind: "register" | "field", draft: Record<string, JsonValue | undefined>): JsonObject {
  const created: JsonObject = {};
  for (const [key, value] of Object.entries(draft)) {
    if (value !== undefined) {
      created[key] = value;
    }
  }
  if (kind === "register" && created.type === "fields") {
    created.fields = [{ name: "field0", type: "bit" }];
  }
  return created;
}
