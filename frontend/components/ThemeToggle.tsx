"use client";

import { useTheme } from "@/components/ThemeProvider";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="theme-toggle"
      aria-label={
        isDark
          ? "Switch to light mode"
          : "Switch to dark mode"
      }
      title={
        isDark
          ? "Switch to light mode"
          : "Switch to dark mode"
      }
    >
      <span
        className="theme-toggle-icon"
        aria-hidden="true"
      >
        {isDark ? "☀" : "☾"}
      </span>

      <span className="theme-toggle-label">
        {isDark ? "Light" : "Dark"}
      </span>
    </button>
  );
}