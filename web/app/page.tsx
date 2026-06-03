"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  BalanceCard,
  DailyStatsCard,
  MonthlyReportCard,
  BudgetCard,
  RatesCard,
  RecentTransactions,
  MonoAccountsCard,
  AccountBalancesCard,
} from "@/components/dashboard";
import { EmptyState } from "@/components/ui/EmptyState";
import { BalanceSkeleton, CardSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import type { Transaction, Balance, BudgetStatus } from "@/lib/types";
import type { FormattedRates } from "@/lib/mono";

function parseDate(dateStr: string): Date {
  const [day, month, year] = dateStr.split(".").map(Number);
  return new Date(year, month - 1, day);
}

function isToday(dateStr: string): boolean {
  const today = new Date();
  const d = parseDate(dateStr);
  return (
    d.getDate() === today.getDate() &&
    d.getMonth() === today.getMonth() &&
    d.getFullYear() === today.getFullYear()
  );
}

function isThisWeek(dateStr: string): boolean {
  const today = new Date();
  const d = parseDate(dateStr);
  const startOfWeek = new Date(today);
  startOfWeek.setDate(today.getDate() - today.getDay());
  startOfWeek.setHours(0, 0, 0, 0);
  const endOfWeek = new Date(startOfWeek);
  endOfWeek.setDate(startOfWeek.getDate() + 6);
  endOfWeek.setHours(23, 59, 59, 999);
  return d >= startOfWeek && d <= endOfWeek;
}

function calcStats(
  transactions: Transaction[],
  filter: (d: string) => boolean,
): { income: number; expense: number; total: number } {
  let income = 0;
  let expense = 0;
  for (const tx of transactions) {
    if (!filter(tx.date)) continue;
    if (tx.transferId?.trim()) continue;
    const amount = tx.amountUah !== "" ? tx.amountUah : 0;
    // Expense amounts are negative in sheet — use abs()
    if (tx.type === "income") {
      income += amount;
    } else if (tx.type === "expense") {
      expense += Math.abs(amount);
    }
  }
  return { income, expense, total: income - expense };
}

export default function DashboardPage() {
  const [balance, setBalance] = useState<Balance | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [budget, setBudget] = useState<BudgetStatus | null>(null);
  const [rates, setRates] = useState<FormattedRates | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const pullDistanceRef = useRef(0);
  const pullStartY = useRef(0);
  const isPulling = useRef(false);
  const [pullDistance, setPullDistance] = useState(0);

  const { showToast } = useToast();

  const fetchData = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true);
      setError(null);

      try {
        const [balanceRes, transactionsRes, budgetRes, ratesRes] =
          await Promise.all([
            fetch("/api/sheets/balance"),
            fetch("/api/sheets/transactions"),
            fetch("/api/sheets/budget"),
            fetch("/api/mono/rates"),
          ]);

        if (!balanceRes.ok) {
          throw new Error(`Balance API: ${balanceRes.status}`);
        }
        if (!transactionsRes.ok) {
          throw new Error(`Transactions API: ${transactionsRes.status}`);
        }

        const balanceJson = await balanceRes.json();
        const transactionsJson = await transactionsRes.json();

        setBalance(balanceJson.data ?? balanceJson);
        const txList = transactionsJson.data ?? transactionsJson;
        setTransactions(Array.isArray(txList) ? txList : []);

        if (budgetRes.ok) {
          const budgetJson = await budgetRes.json();
          setBudget(budgetJson.data ?? budgetJson);
        } else {
          setBudget(null);
        }

        if (ratesRes.ok) {
          const ratesJson = await ratesRes.json();
          if (!ratesJson.error) setRates(ratesJson);
        }

        if (!silent) {
          showToast("success", "Данные обновлены");
        }
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Неизвестная ошибка";
        setError(message);
        showToast("error", "Не удалось загрузить данные");
      } finally {
        setLoading(false);
        setRefreshing(false);
        setPullDistance(0);
        pullDistanceRef.current = 0;
      }
    },
    [showToast],
  );

  useEffect(() => {
    fetchData(true);
  }, []);

  // ── Pull-to-refresh ──
  useEffect(() => {
    const handleTouchStart = (e: TouchEvent) => {
      if (window.scrollY === 0) {
        pullStartY.current = e.touches[0].clientY;
        isPulling.current = true;
      }
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (!isPulling.current) return;
      const delta = e.touches[0].clientY - pullStartY.current;
      if (delta > 0) {
        const distance = Math.min(delta * 0.4, 120);
        pullDistanceRef.current = distance;
        setPullDistance(distance);
        if (delta > 10) e.preventDefault();
      }
    };

    const handleTouchEnd = () => {
      if (!isPulling.current) return;
      isPulling.current = false;
      if (pullDistanceRef.current > 70) {
        setRefreshing(true);
        fetchData(false);
      } else {
        setPullDistance(0);
        pullDistanceRef.current = 0;
      }
    };

    document.addEventListener("touchstart", handleTouchStart, {
      passive: false,
    });
    document.addEventListener("touchmove", handleTouchMove, { passive: false });
    document.addEventListener("touchend", handleTouchEnd);

    return () => {
      document.removeEventListener("touchstart", handleTouchStart);
      document.removeEventListener("touchmove", handleTouchMove);
      document.removeEventListener("touchend", handleTouchEnd);
    };
  }, [fetchData]);

  const handleRefresh = useCallback(() => {
    fetchData(false);
  }, [fetchData]);

  // ── Monthly stats (useMemo BEFORE conditional returns) ──
  const CURRENT_MONTH_NAME = new Date().toLocaleString("en-US", {
    month: "long",
  });
  const CURRENT_MONTH_LABEL = new Date().toLocaleString("ru-RU", {
    month: "long",
    year: "numeric",
  });

  const monthStats = useMemo(() => {
    let income = 0;
    let expense = 0;
    const catMap = new Map<string, number>();
    for (const tx of transactions) {
      if (tx.month !== CURRENT_MONTH_NAME) continue;
      if (tx.transferId?.trim()) continue;
      const amount = tx.amountUah !== "" ? tx.amountUah : 0;
      if (tx.type === "income") {
        income += amount;
      } else if (tx.type === "expense") {
        const absAmount = Math.abs(amount);
        expense += absAmount;
        if (absAmount > 0) {
          const cat = tx.category?.trim() || "Другое";
          catMap.set(cat, (catMap.get(cat) ?? 0) + absAmount);
        }
      }
    }
    const topCategories = Array.from(catMap.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([category, amount]) => ({
        category,
        amount,
        percentage: expense > 0 ? (amount / expense) * 100 : 0,
        currency: "UAH" as const,
      }));
    return { income, expense, topCategories };
  }, [transactions]);

  const hasMonthData = monthStats.income > 0 || monthStats.expense > 0;

  // ── Error state ──
  if (error && !loading) {
    return (
      <div className="space-y-4">
        <BalanceCard balance={null} loading={false} />
        <EmptyState
          icon="😿"
          description={`Что-то сломалось. Кеша расстроен. (${error})`}
        />
        <button
          onClick={handleRefresh}
          className="w-full py-3 px-4 rounded-xl bg-kesha-card border border-kesha-border text-kesha-accent font-medium text-sm hover:bg-kesha-card-hover transition-colors"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  // ── Loading state ──
  if (loading) {
    return (
      <div className="space-y-4">
        <BalanceSkeleton />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
        <CardSkeleton />
        <div className="bg-kesha-card rounded-xl border border-kesha-border p-5 space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="flex items-center gap-3 py-3 border-b border-kesha-border last:border-0"
            >
              <div className="h-8 w-8 rounded-full bg-kesha-border animate-pulse" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3.5 w-28 bg-kesha-border animate-pulse rounded" />
                <div className="h-3 w-20 bg-kesha-border animate-pulse rounded" />
              </div>
              <div className="h-4 w-16 bg-kesha-border animate-pulse rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ── Computed stats ──
  const todayStats = calcStats(transactions, isToday);
  const weekStats = calcStats(transactions, isThisWeek);

  return (
    <div className="space-y-4">
      {/* Pull-to-refresh indicator */}
      <div
        className="flex justify-center overflow-hidden transition-all duration-200"
        style={{
          height: `${pullDistance}px`,
          opacity: pullDistance > 20 ? 1 : 0,
        }}
      >
        <div className="flex items-center gap-2 text-xs text-kesha-text-tertiary">
          <svg
            className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            style={{
              transform: `rotate(${Math.min(pullDistance * 2, 360)}deg)`,
            }}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
            />
          </svg>
          <span>
            {refreshing
              ? "Обновляем..."
              : pullDistance > 70
                ? "Отпусти, чтобы обновить"
                : "Тяни вниз, чтобы обновить"}
          </span>
        </div>
      </div>

      {/* Header greeting */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-kesha-text-primary">
          Сводка
        </h1>
        <button
          onClick={handleRefresh}
          className="p-2 rounded-lg text-kesha-text-tertiary hover:text-kesha-accent hover:bg-kesha-card-hover transition-colors"
          title="Обновить"
        >
          <svg
            className={`w-5 h-5 transition-transform duration-300 ${refreshing || loading ? "animate-spin" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
            />
          </svg>
        </button>
      </div>

      {/* 1. Balance */}
      <div className="animate-fade-in">
        <BalanceCard balance={balance} loading={false} />
      </div>

      {/* 1.5 Monobank accounts */}
      <MonoAccountsCard />

      {/* 1.6 Account balances from transactions */}
      <AccountBalancesCard />

      {/* 2. Today + Week stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DailyStatsCard
          title="Сегодня"
          income={todayStats.income}
          expense={todayStats.expense}
          total={todayStats.total}
          loading={false}
        />
        <DailyStatsCard
          title="Неделя"
          income={weekStats.income}
          expense={weekStats.expense}
          total={weekStats.total}
          loading={false}
        />
      </div>

      {/* 2.5 Monthly report */}
      <MonthlyReportCard
        monthLabel={CURRENT_MONTH_LABEL}
        income={monthStats.income}
        expense={monthStats.expense}
        categories={monthStats.topCategories}
        loading={false}
        empty={!hasMonthData}
      />

      {/* 3. Budget */}
      <BudgetCard budget={budget} loading={false} />

      {/* 4. Currency rates */}
      <RatesCard rates={rates} />

      {/* 5. Recent transactions */}
      <RecentTransactions transactions={transactions} loading={false} />
    </div>
  );
}
