// The JSON-RPC 2.0 messages between the editor and bust, as
// bust/editing/bridge.py answers them.

export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

// Keys and list indexes from the top of the register map down to one value.
export type ValuePath = (string | number)[];

export type Operation =
  | { op: "add"; path: string; value: JsonValue }
  | { op: "replace"; path: string; value: JsonValue }
  | { op: "remove"; path: string };

export type Problem = {
  path: ValuePath;
  location: string;
  message: string;
  line: number | null;
};

// A run of bits in a register, from the highest down, as bust's documentation
// draws it: a field, the whole register, or bits no field uses.
export type BitSegment = {
  name: string;
  high: number;
  low: number;
  reset: string;
  isUnused: boolean;
};

export type FieldLayout = {
  low: number;
  high: number;
  // Software and hardware access with defaults filled in, such as "RW/R".
  access: string;
  reset: string;
};

// A register as bust reads it, with the defaults filled in.
export type RegisterLayout = {
  address: number;
  width: number;
  type: string;
  access: string;
  reset: string;
  segments: BitSegment[];
  fields: Record<string, FieldLayout>;
};

export type AcceptedState = {
  accepted: true;
  data: JsonObject;
  text: string;
  warnings: string[];
  // Where bust places each register, by name.
  layout: Record<string, RegisterLayout>;
  // The address bust gives a register added without one.
  nextAddress: number;
  canUndo: boolean;
  canRedo: boolean;
};

export type RejectedState = {
  accepted: false;
  problems: Problem[];
};

export type EditorState = AcceptedState | RejectedState;

export type JsonSchema = {
  type?: string | string[];
  enum?: string[];
  anyOf?: JsonSchema[];
  default?: JsonValue;
  description?: string;
  required?: string[];
  properties?: Record<string, JsonSchema>;
  items?: JsonSchema;
  $ref?: string;
  $defs?: Record<string, JsonSchema>;
};

export type BridgeMethods = {
  schema: { params: Record<string, never>; result: JsonSchema };
  open: { params: { text: string }; result: EditorState };
  new: { params: { bus: JsonObject; module: JsonObject }; result: EditorState };
  apply: { params: { operations: Operation[] }; result: EditorState };
  undo: { params: Record<string, never>; result: EditorState };
  redo: { params: Record<string, never>; result: EditorState };
};

export type BridgeMethod = keyof BridgeMethods;

// Carries one JSON-RPC request to bust and brings back its response: a
// Pyodide worker in cloudbust, a bust process over stdio on the desktop.
export type Transport = (request: string) => Promise<string>;

type Response = {
  id: number;
  result?: unknown;
  error?: { code: number; message: string };
};

export class BustBridge {
  private nextId = 0;

  constructor(private readonly transport: Transport) {}

  async call<M extends BridgeMethod>(
    method: M,
    params: BridgeMethods[M]["params"],
  ): Promise<BridgeMethods[M]["result"]> {
    const request = { jsonrpc: "2.0", id: this.nextId++, method, params };
    const response: Response = JSON.parse(await this.transport(JSON.stringify(request)));
    if (response.error) {
      throw new Error(response.error.message);
    }
    return response.result as BridgeMethods[M]["result"];
  }
}

// RFC 6901: ~ and / in a key are escaped.
export function pointer(path: ValuePath): string {
  return path.map((token) => "/" + String(token).replace(/~/g, "~0").replace(/\//g, "~1")).join("");
}
