"use client";

import { useState, useEffect } from "react";
import { getRandomQuote } from "@/lib/quotes";

export function Header() {
  const [quote, setQuote] = useState("");

  useEffect(() => {
    setQuote(getRandomQuote());
  }, []);

  return (
    <header className="sticky top-0 z-40 bg-kesha-page/80 backdrop-blur-md border-b border-kesha-border">
      <div className="mx-auto max-w-lg px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl" role="img" aria-label="Кеша">
              🐿️
            </span>
            <h1 className="text-xl font-bold text-kesha-accent tracking-tight">
              Кеша
            </h1>
          </div>
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
