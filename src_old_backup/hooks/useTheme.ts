import { useEffect, useState } from "react";

export type Theme = "light" | "dark";

const THEME_KEY = "claimbridge-theme";

function getInitialTheme(): Theme {
  if (typeof window === "undefined") {
    return "dark";
  }

  const stored = window.localStorage.getItem(THEME_KEY);

  if (stored === "dark" || stored === "light") {
    return stored;
  }

  return "dark"; // Default to Dark Mode
}

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") {
    return;
  }

  document.documentElement.setAttribute("data-theme", theme);

  if (theme === "dark") {
    document.documentElement.classList.add("dark");
    document.documentElement.classList.remove("light");
  } else {
    document.documentElement.classList.remove("dark");
    document.documentElement.classList.add("light");
  }
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    applyTheme(theme);
    window.localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  function setTheme(newTheme: Theme) {
    setThemeState(newTheme);
  }

  function toggleTheme() {
    setThemeState((current) => (current === "light" ? "dark" : "light"));
  }

  return {
    theme,
    setTheme,
    toggleTheme,
    isDark: theme === "dark",
  };
}