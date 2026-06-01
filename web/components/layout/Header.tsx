"use client";

import { useState, useEffect, useCallback } from "react";
import { getRandomQuote } from "@/lib/quotes";

type Theme = "system" | "dark" | "light";

function getStoredTheme(): Theme {
  if (typeof window === "undefined") return "system";
  const stored = localStorage.getItem("theme");
  if (stored === "dark" || stored === "light") return stored;
  return "system";
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  root.classList.remove("dark", "light");
  if (theme === "system") {
    localStorage.removeItem("theme");
    if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      root.classList.add("dark");
    }
  } else {
    localStorage.setItem("theme", theme);
    root.classList.add(theme);
  }
}

function nextTheme(current: Theme): Theme {
  if (current === "system") return "dark";
  if (current === "dark") return "light";
  return "system";
}

export function Header() {
  const [quote, setQuote] = useState("");
  const [theme, setTheme] = useState<Theme>("system");

  useEffect(() => {
    setQuote(getRandomQuote());
  }, []);

  useEffect(() => {
    setTheme(getStoredTheme());
  }, []);

  const toggleTheme = useCallback(() => {
    const next = nextTheme(theme);
    applyTheme(next);
    setTheme(next);
  }, [theme]);

  return (
    <header className="sticky top-0 z-40 bg-kesha-page/80 backdrop-blur-md border-b border-kesha-border pt-safe">
      <div className="mx-auto max-w-lg md:max-w-2xl px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl" role="img" aria-label="Кеша">
              🐿️
            </span>
            <div>
              <h1 className="text-xl font-bold text-kesha-accent tracking-tight">
                Кеша
              </h1>
              <p className="text-[10px] text-kesha-text-tertiary tracking-wide uppercase leading-none">
                Трать с умом, хомяк
              </p>
            </div>
          </div>

          <button
            onClick={toggleTheme}
            className="w-9 h-9 rounded-lg flex items-center justify-center text-kesha-text-secondary hover:text-kesha-accent hover:bg-kesha-card-hover active:scale-95 transition-all"
            aria-label="Переключить тему"
          >
            {theme === "system" ? (
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0V12a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 12V5.25"
                />
              </svg>
            ) : theme === "dark" ? (
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z"
                />
              </svg>
            ) : (
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"
                />
              </svg>
            )}
          </button>
        </div>
        {quote && (
          <p className="mt-1 text-xs text-kesha-text-secondary italic leading-relaxed line-clamp-2 pr-4">
            «{quote}»
          </p>
        )}
      </div>
    </header>
  );
}
