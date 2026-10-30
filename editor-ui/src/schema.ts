import type { JsonSchema, JsonValue } from "./protocol.js";

export type NodeKind = "bus" | "module" | "register" | "field";

// How a key is edited, worked out from its schema.
export type InputKind = "choice" | "flag" | "either" | "number" | "text" | "longtext" | "list";

const LABELS: Record<string, string> = {
  addr_width: "Address width",
  data_width: "Data width",
  byte_addressable: "Byte addressable",
  sw: "Software access",
  hw: "Hardware access",
  onread: "On read",
  onwrite: "On write",
  singlepulse: "Single pulse",
  we: "Write enable (we)",
  wel: "Write enable, active low (wel)",
  hwset: "Hardware set (hwset)",
  hwclr: "Hardware clear (hwclr)",
  swmod: "Software modified strobe (swmod)",
  swacc: "Software access strobe (swacc)",
  reset: "Reset value",
};

// Access keys that most registers leave at their defaults, so the form puts
// them out of the way.
export const ADVANCED_KEYS = new Set(["onread", "onwrite", "singlepulse", "we", "wel", "hwset", "hwclr", "swmod", "swacc"]);

export const ACCESS_KEYS = new Set(["sw", "hw", ...ADVANCED_KEYS]);

export function labelOf(key: string): string {
  return LABELS[key] ?? key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, " ");
}

export function definitionOf(schema: JsonSchema, kind: NodeKind): JsonSchema {
  const definition = schema.$defs?.[kind];
  if (!definition) {
    throw new Error(`The schema has no definition of a ${kind}`);
  }
  return definition;
}

export function inputKindOf(key: string, property: JsonSchema): InputKind {
  if (property.enum) {
    return "choice";
  }
  if (property.anyOf) {
    return "number";
  }
  const types = Array.isArray(property.type) ? property.type : [property.type];
  if (types.includes("array")) {
    return "list";
  }
  if (types.includes("boolean")) {
    // Without a default, leaving the key out means something of its own.
    return property.default === undefined ? "either" : "flag";
  }
  return key === "description" ? "longtext" : "text";
}

// The text an input shows for a value that is not set.
export function placeholderOf(property: JsonSchema): string {
  if (property.default !== undefined && property.default !== "" && property.default !== false) {
    return `Default: ${String(property.default)}`;
  }
  const match = property.description?.match(/Default: ([^.]+)\./);
  return match ? `Default: ${match[1]}` : "";
}

// A number as the user typed it: decimal digits become a JSON number, any
// other form (0x1c, 0b101) stays a string, as bust reads both.
export function parseNumber(text: string): JsonValue | undefined {
  const trimmed = text.trim();
  if (trimmed === "") {
    return undefined;
  }
  return /^[0-9]+$/.test(trimmed) ? Number(trimmed) : trimmed;
}
