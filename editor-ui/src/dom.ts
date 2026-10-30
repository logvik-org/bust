export function element<K extends keyof HTMLElementTagNameMap>(
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

export function hex(value: number, digits: number): string {
  return "0x" + value.toString(16).toUpperCase().padStart(digits, "0");
}

export function bitRange(low: number, high: number): string {
  return low === high ? `[${low}]` : `[${high}:${low}]`;
}
