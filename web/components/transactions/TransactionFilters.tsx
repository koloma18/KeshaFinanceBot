"use client";

import { useState, useCallback } from "react";

export interface FilterState {
  type: "all" | "income" | "expense";
  category: string;
  dateFrom: string;
  dateTo: string;
  search: string;
}

interface TransactionFiltersProps {
  categories: string[];
  onFilterChange: (filters: FilterState) => void;
}

// ── Date presets ──

function todayStr(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function daysAgoStr(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

interface Preset {
  label: string;
  get: () => { from: string; to: string };
}

const PRESETS: Preset[] = [
  { label: "Сегодня", get: () => ({ from: todayStr(), to: todayStr() }) },
  { label: "Неделя", get: () => ({ from: daysAgoStr(7), to: todayStr() }) },
  { label: "Месяц", get: () => ({ from: daysAgoStr(30), to: todayStr() }) },
  { label: "Всё", get: () => ({ from: "", to: "" }) },
];

export function TransactionFilters({
  categories,
  onFilterChange,
}: TransactionFiltersProps) {
  const [open, setOpen] = useState(false);

  const [filters, setFilters] = useState<FilterState>({
    type: "all",
    category: "",
    dateFrom: "",
    dateTo: "",
    search: "",
  });

  function update(partial: Partial<FilterState>) {
    const next = { ...filters, ...partial };
    setFilters(next);
    onFilterChange(next);
  }

  function reset() {
    const cleared: FilterState = {
      type: "all",
      category: "",
      dateFrom: "",
      dateTo: "",
      search: "",
    };
    setFilters(cleared);
    onFilterChange(cleared);
  }

  const hasActiveFilters =
    filters.type !== "all" ||
    filters.category !== "" ||
    filters.dateFrom !== "" ||
    filters.dateTo !== "" ||
    filters.search !== "";

  return (
    <div className="space-y-2">
      {/* Date presets */}
      <div className="flex gap-1.5 flex-wrap">
        {PRESETS.map((preset) => {
          const { from, to } = preset.get();
          const isActive = filters.dateFrom === from && filters.dateTo === to;
          return (
            <button
              key={preset.label}
              onClick={() => update({ dateFrom: from, dateTo: to })}
              className={`rounded-lg px-3 py-1 text-xs font-medium transition-colors ${
                isActive
                  ? "bg-kesha-accent-bg text-kesha-accent"
                  : "bg-kesha-card-hover text-kesha-text-secondary hover:text-kesha-text-primary"
              }`}
            >
              {preset.label}
            </button>
          );
        })}
      </div>

      {/* Toggle button — mobile only */}
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between rounded-lg bg-kesha-card border border-kesha-border px-4 py-2.5 text-sm text-kesha-text-primary lg:hidden"
      >
        <span className="flex items-center gap-2">
          <span>🔍</span>
          <span>Фильтры</span>
          {hasActiveFilters && (
            <span className="h-2 w-2 rounded-full bg-kesha-accent" />
          )}
        </span>
        <svg
          className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Filter bar */}
      <div
        className={`flex flex-col gap-3 lg:flex lg:flex-row lg:flex-wrap lg:items-end ${
          open ? "block" : "hidden lg:flex"
        }`}
      >
        {/* Type */}
        <div className="flex-1 min-w-[140px]">
          <label className="mb-1 block text-xs text-kesha-text-tertiary">
            Тип
          </label>
          <select
            value={filters.type}
            onChange={(e) =>
              update({ type: e.target.value as FilterState["type"] })
            }
            className="w-full rounded-lg border border-kesha-border bg-kesha-card px-3 py-2 text-sm text-kesha-text-primary outline-none focus:border-kesha-accent/50"
          >
            <option value="all">Все</option>
            <option value="income">Доход</option>
            <option value="expense">Расход</option>
          </select>
        </div>

        {/* Category */}
        <div className="flex-1 min-w-[160px]">
          <label className="mb-1 block text-xs text-kesha-text-tertiary">
            Категория
          </label>
          <select
            value={filters.category}
            onChange={(e) => update({ category: e.target.value })}
            className="w-full rounded-lg border border-kesha-border bg-kesha-card px-3 py-2 text-sm text-kesha-text-primary outline-none focus:border-kesha-accent/50"
          >
            <option value="">Все категории</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>

        {/* Date from */}
        <div className="flex-1 min-w-[140px]">
          <label className="mb-1 block text-xs text-kesha-text-tertiary">
            Дата с
          </label>
          <input
            type="date"
            value={filters.dateFrom}
            onChange={(e) => update({ dateFrom: e.target.value })}
            className="w-full rounded-lg border border-kesha-border bg-kesha-card px-3 py-2 text-sm text-kesha-text-primary outline-none focus:border-kesha-accent/50 [color-scheme:dark]"
          />
        </div>

        {/* Date to */}
        <div className="flex-1 min-w-[140px]">
          <label className="mb-1 block text-xs text-kesha-text-tertiary">
            Дата по
          </label>
          <input
            type="date"
            value={filters.dateTo}
            onChange={(e) => update({ dateTo: e.target.value })}
            className="w-full rounded-lg border border-kesha-border bg-kesha-card px-3 py-2 text-sm text-kesha-text-primary outline-none focus:border-kesha-accent/50 [color-scheme:dark]"
          />
        </div>

        {/* Search */}
        <div className="flex-1 min-w-[160px]">
          <label className="mb-1 block text-xs text-kesha-text-tertiary">
            Поиск
          </label>
          <input
            type="text"
            placeholder="Комментарий…"
            value={filters.search}
            onChange={(e) => update({ search: e.target.value })}
            className="w-full rounded-lg border border-kesha-border bg-kesha-card px-3 py-2 text-sm text-kesha-text-primary placeholder:text-kesha-text-tertiary outline-none focus:border-kesha-accent/50"
          />
        </div>

        {/* Reset */}
        <div className="flex-none">
          {hasActiveFilters && (
            <button
              onClick={reset}
              className="flex items-center gap-1 rounded-lg bg-kesha-card-hover px-3 py-2 text-sm text-kesha-text-secondary hover:text-kesha-text-primary transition-colors"
            >
              <span>✕</span>
              <span className="hidden sm:inline">Сбросить</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
