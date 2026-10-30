import { element } from "./dom.js";
import type { BitSegment } from "./protocol.js";

// A register's bits from the highest down, drawn as bust's documentation
// draws them: a box per field with its name, its bit numbers above and its
// reset value below. Unused bits are a dashed box.
export function bitDiagram(
  segments: BitSegment[],
  selectedName: string | undefined,
  onSelect?: (name: string) => void,
): HTMLElement {
  const width = segments.reduce((highest, segment) => Math.max(highest, segment.high + 1), 0);
  const diagram = element("div", { class: "bust-editor-diagram", role: "group", "aria-label": "Bits" });
  diagram.style.setProperty("--bust-editor-bit-count", String(width));
  for (const segment of segments) {
    const column = `${width - segment.high} / ${width - segment.low + 1}`;
    const numbers =
      segment.high === segment.low
        ? [element("span", {}, String(segment.high))]
        : [element("span", {}, String(segment.high)), element("span", {}, String(segment.low))];
    const label = element("span", { class: "bust-editor-diagram-bits" }, ...numbers);
    const box = segment.isUnused || !onSelect
      ? element("span", { class: "bust-editor-diagram-box" }, element("span", {}, segment.isUnused ? "" : segment.name))
      : element("button", { type: "button", class: "bust-editor-diagram-box", title: segment.name }, element("span", {}, segment.name));
    if (box instanceof HTMLButtonElement) {
      box.addEventListener("click", () => onSelect!(segment.name));
      if (segment.name === selectedName) {
        box.setAttribute("aria-current", "true");
      }
    }
    const reset = element("span", { class: "bust-editor-diagram-reset" }, segment.reset);
    const cell = element("div", { class: "bust-editor-diagram-segment" }, label, box, reset);
    if (segment.isUnused) {
      cell.classList.add("bust-editor-unused");
    }
    cell.style.gridColumn = column;
    diagram.append(cell);
  }
  return diagram;
}
