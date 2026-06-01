"use client";

import { useState, useEffect } from "react";

interface ChartColors {
  border: string;
  textSecondary: string;
  textPrimary: string;
  card: string;
  income: string;
  expense: string;
  pie: string[];
}

function getComputedCSSVar(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

function detectColors(): ChartColors {
  const isDark =
    typeof window !== "undefined" &&
    document.documentElement.classList.contains("dark");

  return {
    border:
      getComputedCSSVar("--color-border") || (isDark ? "#334155" : "#e2e8f0"),
    textSecondary:
      getComputedCSSVar("--color-text-secondary") ||
      (isDark ? "#94a3b8" : "#475569"),
    textPrimary:
      getComputedCSSVar("--color-text-primary") ||
      (isDark ? "#f1f5f9" : "#0f172a"),
    card: getComputedCSSVar("--color-card") || (isDark ? "#1e293b" : "#ffffff"),
    income:
      getComputedCSSVar("--color-income") || (isDark ? "#34d399" : "#059669"),
    expense:
      getComputedCSSVar("--color-expense") || (isDark ? "#f87171" : "#dc2626"),
    pie: isDark
      ? [
          "#f87171",
          "#fb923c",
          "#fbbf24",
          "#a3e635",
          "#34d399",
          "#2dd4bf",
          "#38bdf8",
          "#818cf8",
          "#a78bfa",
          "#e879f9",
          "#f472b6",
          "#94a3b8",
        ]
      : [
          "#ef4444",
          "#f97316",
          "#d97706",
          "#65a30d",
          "#059669",
          "#0d9488",
          "#0284c7",
          "#4f46e5",
          "#7c3aed",
          "#c026d3",
          "#db2777",
          "#475569",
        ],
  };
}

export function useChartColors(): ChartColors {
  const [colors, setColors] = useState<ChartColors>(() => ({
    border: "#334155",
    textSecondary: "#94a3b8",
    textPrimary: "#f1f5f9",
    card: "#1e293b",
    income: "#34d399",
    expense: "#f87171",
    pie: [
      "#f87171",
      "#fb923c",
      "#fbbf24",
      "#a3e635",
      "#34d399",
      "#2dd4bf",
      "#38bdf8",
      "#818cf8",
      "#a78bfa",
      "#e879f9",
      "#f472b6",
      "#94a3b8",
    ],
  }));

  useEffect(() => {
    setColors(detectColors());

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const observer = new MutationObserver(() => setColors(detectColors()));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    mq.addEventListener("change", () => setColors(detectColors()));

    return () => {
      observer.disconnect();
      mq.removeEventListener("change", () => setColors(detectColors()));
    };
  }, []);

  return colors;
}
