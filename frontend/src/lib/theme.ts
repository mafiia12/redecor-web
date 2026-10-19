import { useSyncExternalStore } from "react";
import { THEME } from "../config";

export type Mode = "dark" | "light";
const KEY = "redecor-theme";
const listeners = new Set<() => void>();

function stored(): Mode | null {
  try {
    const v = localStorage.getItem(KEY);
    return v === "dark" || v === "light" ? v : null;
  } catch {
    return null;
  }
}

export function currentMode(): Mode {
  const d = document.documentElement.dataset.theme;
  return d === "dark" || d === "light" ? d : THEME;
}

function apply(m: Mode) {
  document.documentElement.dataset.theme = m;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", m === "dark" ? "#0a0a0b" : "#fafaf8");
  listeners.forEach((l) => l());
}

/** Called once at startup: the visitor's saved choice wins over the site default (THEME in config.ts). */
export function initTheme() {
  apply(stored() ?? THEME);
}

export function toggleTheme() {
  const next: Mode = currentMode() === "dark" ? "light" : "dark";
  try {
    localStorage.setItem(KEY, next);
  } catch {
    /* private mode: the choice just lasts for this visit */
  }
  apply(next);
}

export function useMode(): Mode {
  return useSyncExternalStore(
    (cb) => (listeners.add(cb), () => listeners.delete(cb)),
    currentMode,
    () => THEME,
  );
}
