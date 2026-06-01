"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { Transaction } from "@/lib/types";
import {
  TransactionFilters,
  FilterState,
} from "@/components/transactions/TransactionFilters";
import { TransactionTable } from "@/components/transactions/TransactionTable";
import { Pagination } from "@/components/transactions/Pagination";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";

const CATEGORIES = [
  "Кофе",
  "Еда",
  "Такси",
  "Одежда",
  "Красота",
  "Подписки",
  "Дом",
  "Подарки",
  "Маркетплейсы",
  "Здоровье",
  "Развлечения",
  "Зарплата",
  "Фриланс",
  "Подарок",
  "Инвестиции",
  "Возврат долга",
  "Другое",
];

const PAGE_SIZE = 50;

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showBackToTop, setShowBackToTop] = useState(false);

  const [filters, setFilters] = useState<FilterState>({
    type: "all",
    category: "",
    dateFrom: "",
    dateTo: "",
    search: "",
  });

  const [sortConfig, setSortConfig] = useState<{
    column: string;
    direction: "asc" | "desc";
  }>({ column: "date", direction: "desc" });

  const [page, setPage] = useState(1);
  const [allCategories, setAllCategories] = useState<string[]>(CATEGORIES);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch("/api/sheets/transactions");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: Transaction[] = await res.json();
        setTransactions(data);

        const cats = new Set<string>();
        data.forEach((tx) => {
          if (tx.category) cats.add(tx.category);
        });
        if (cats.size > 0) {
          setAllCategories(Array.from(cats).sort());
        }
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Не удалось загрузить транзакции",
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Back to top visibility
  useEffect(() => {
    const handleScroll = () => {
      setShowBackToTop(window.scrollY > 300);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    setPage(1);
  }, [filters]);

  const handleFilterChange = useCallback(
    (next: FilterState) => setFilters(next),
    [],
  );

  const handleSort = useCallback((column: string) => {
    setSortConfig((prev) => ({
      column,
      direction:
        prev.column === column && prev.direction === "asc" ? "desc" : "asc",
    }));
  }, []);

  const filtered = useMemo(() => {
    let result = [...transactions];

    if (filters.type !== "all") {
      result = result.filter((tx) => tx.type === filters.type);
    }

    if (filters.category !== "") {
      result = result.filter((tx) => tx.category === filters.category);
    }

    if (filters.dateFrom) {
      const [y, m, d] = filters.dateFrom.split("-").map(Number);
      const from = new Date(y, m - 1, d);
      result = result.filter((tx) => {
        const parts = tx.date.split(".");
        const txDate = new Date(
          parseInt(parts[2]),
          parseInt(parts[1]) - 1,
          parseInt(parts[0]),
        );
        return txDate >= from;
      });
    }

    if (filters.dateTo) {
      const [y, m, d] = filters.dateTo.split("-").map(Number);
      const to = new Date(y, m - 1, d + 1);
      result = result.filter((tx) => {
        const parts = tx.date.split(".");
        const txDate = new Date(
          parseInt(parts[2]),
          parseInt(parts[1]) - 1,
          parseInt(parts[0]),
        );
        return txDate <= to;
      });
    }

    if (filters.search.trim()) {
      const q = filters.search.trim().toLowerCase();
      result = result.filter(
        (tx) =>
          tx.comment.toLowerCase().includes(q) ||
          tx.category.toLowerCase().includes(q),
      );
    }

    result.sort((a, b) => {
      let cmp = 0;

      if (sortConfig.column === "date") {
        const aParts = a.date.split(".");
        const bParts = b.date.split(".");
        const aDate = new Date(
          parseInt(aParts[2]),
          parseInt(aParts[1]) - 1,
          parseInt(aParts[0]),
        );
        const bDate = new Date(
          parseInt(bParts[2]),
          parseInt(bParts[1]) - 1,
          parseInt(bParts[0]),
        );
        cmp = aDate.getTime() - bDate.getTime();
      } else if (sortConfig.column === "category") {
        cmp = a.category.localeCompare(b.category);
      }

      return sortConfig.direction === "asc" ? cmp : -cmp;
    });

    return result;
  }, [transactions, filters, sortConfig]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const paginated = filtered.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE,
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Транзакции</CardTitle>
          {!loading && transactions.length > 0 && (
            <p className="mt-1 text-xs text-kesha-accent italic leading-relaxed">
              🐿️ «Все транзакции перед тобой. Кеша следит за каждой.»
            </p>
          )}
          {!loading && (
            <p className="mt-1 text-xs text-kesha-text-tertiary">
              Всего:{" "}
              <span className="text-kesha-text-primary font-medium tabular-nums">
                {filtered.length}
              </span>
              {filtered.length !== transactions.length && (
                <span className="text-kesha-text-tertiary">
                  {" "}
                  (из {transactions.length})
                </span>
              )}
            </p>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          <TransactionFilters
            categories={allCategories}
            onFilterChange={handleFilterChange}
          />

          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 py-3 border-b border-kesha-border last:border-0"
                >
                  <Skeleton className="h-8 w-8 rounded-full" />
                  <div className="flex-1 space-y-1.5">
                    <Skeleton className="h-3.5 w-28" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                  <Skeleton className="h-4 w-16" />
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="py-8 text-center">
              <p className="text-sm text-kesha-expense mb-2">⚠️ {error}</p>
              <p className="text-xs text-kesha-text-secondary">
                Кеша не может достучаться до таблицы. Попробуй позже или проверь
                API.
              </p>
            </div>
          ) : filtered.length === 0 && transactions.length === 0 ? (
            <EmptyState
              variant="transactions"
              description="Пока нет ни одной транзакции. Добавь первую через бота, и Кеша начнёт считать твои деньги."
            />
          ) : filtered.length === 0 ? (
            <EmptyState variant="transactions" />
          ) : (
            <>
              <TransactionTable
                transactions={paginated}
                sortConfig={sortConfig}
                onSort={handleSort}
              />
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>

      {/* Back to Top */}
      {showBackToTop && (
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="fixed bottom-20 right-4 z-40 w-10 h-10 rounded-full bg-kesha-accent text-black shadow-lg flex items-center justify-center transition-all hover:scale-110 active:scale-95 animate-fade-scale"
          aria-label="Наверх"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4.5 15.75l7.5-7.5 7.5 7.5"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
