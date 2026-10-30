import { element } from "./dom.js";

export type MenuItem =
  | {
      label: string;
      action: () => void;
      // The key that does the same outside the menu, shown beside the label.
      shortcut?: string;
      isDisabled?: boolean;
      isDangerous?: boolean;
    }
  | "separator";

// A pop-up menu of actions, at a point or under a button. Arrow keys move,
// Enter picks, Escape or a click elsewhere closes it and gives focus back.
export class PopupMenu {
  private readonly list = element("ul", { class: "bust-editor-menu", role: "menu" });
  private returnFocus?: HTMLElement;

  constructor(private readonly host: HTMLElement) {
    this.list.hidden = true;
    host.append(this.list);
    this.list.addEventListener("keydown", (event) => this.onKey(event));
    document.addEventListener("pointerdown", (event) => {
      if (!this.list.hidden && !this.list.contains(event.target as Node)) {
        this.close(false);
      }
    });
  }

  get isOpen(): boolean {
    return !this.list.hidden;
  }

  openAt(x: number, y: number, title: string, items: MenuItem[], returnFocus?: HTMLElement): void {
    this.returnFocus = returnFocus ?? (document.activeElement as HTMLElement | undefined);
    this.list.setAttribute("aria-label", title);
    this.list.replaceChildren(element("li", { class: "bust-editor-menu-title", role: "presentation" }, title), ...items.map((item) => this.item(item)));
    this.list.hidden = false;
    const hostBox = this.host.getBoundingClientRect();
    const menuBox = this.list.getBoundingClientRect();
    // Keeps the menu inside the window.
    const left = Math.min(x, window.innerWidth - menuBox.width - 8) - hostBox.left;
    const top = (y + menuBox.height > window.innerHeight - 8 ? y - menuBox.height : y) - hostBox.top;
    this.list.style.left = `${Math.max(left, 0)}px`;
    this.list.style.top = `${Math.max(top, 0)}px`;
    this.focusable()[0]?.focus();
  }

  openBelow(anchor: HTMLElement, title: string, items: MenuItem[]): void {
    const box = anchor.getBoundingClientRect();
    this.openAt(box.left, box.bottom + 2, title, items, anchor);
  }

  close(shouldRestoreFocus = true): void {
    if (this.list.hidden) {
      return;
    }
    this.list.hidden = true;
    if (shouldRestoreFocus) {
      this.returnFocus?.focus();
    }
  }

  private item(item: MenuItem): HTMLLIElement {
    if (item === "separator") {
      return element("li", { class: "bust-editor-menu-separator", role: "separator" });
    }
    const button = element(
      "button",
      { type: "button", role: "menuitem", tabindex: "-1" },
      element("span", {}, item.label),
      element("kbd", {}, item.shortcut ?? ""),
    );
    button.disabled = item.isDisabled ?? false;
    if (item.isDangerous) {
      button.classList.add("bust-editor-danger");
    }
    button.addEventListener("click", () => {
      this.close();
      item.action();
    });
    return element("li", { role: "none" }, button);
  }

  private focusable(): HTMLButtonElement[] {
    return [...this.list.querySelectorAll<HTMLButtonElement>("button:not(:disabled)")];
  }

  private onKey(event: KeyboardEvent): void {
    const items = this.focusable();
    const index = items.indexOf(document.activeElement as HTMLButtonElement);
    const moves: Record<string, number> = { ArrowDown: index + 1, ArrowUp: index - 1, Home: 0, End: items.length - 1 };
    if (event.key in moves) {
      event.preventDefault();
      items[(moves[event.key] + items.length) % items.length]?.focus();
    } else if (event.key === "Escape" || event.key === "Tab") {
      event.preventDefault();
      this.close();
    }
  }
}
