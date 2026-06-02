"use client";

import { useState, useEffect, useMemo } from "react";
import { Transaction } from "@/lib/types";
import { MonthlyChart } from "@/components/analytics/MonthlyChart";
import { CategoryPieChart } from "@/components/analytics/CategoryPieChart";
import { PeriodCompare } from "@/components/analytics/PeriodCompare";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatCurrency } from "@/lib/formatters";

export default function AnalyticsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<12 | 6 | 3>(12);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch("/api/sheets/transactions");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: Transaction[] = await res.json();
        setTransactions(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Не удалось загрузить данные",
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const totals = useMemo(() => {
    const now = new Date();
    const cutOff = new Date(now.getFullYear(), now.getMonth() - period + 1, 1);

    let income = 0;
    let expense = 0;

    for (const tx of transactions) {
      const parts = tx.date.split(".");
      if (parts.length !== 3) continue;
      const d = new Date(
        parseInt(parts[2]),
        parseInt(parts[1]) - 1,
        parseInt(parts[0]),
      );
      if (d < cutOff) continue;

      const amount =
        tx.amountUah !== ""
          ? tx.amountUah
          : tx.amountUsd !== ""
            ? tx.amountUsd
            : tx.amountEur !== ""
              ? tx.amountEur
              : 0;

      if (tx.type === "income") income += amount;
      else if (tx.type === "expense") expense += Math.abs(amount);
    }

    return { income: Math.round(income), expense: Math.round(expense) };
  }, [transactions, period]);

  const netResult = totals.income - totals.expense;

  const keshaInsight = useMemo(() => {
    if (totals.income === 0 && totals.expense === 0) return null;
    const ratio = totals.income > 0 ? totals.expense / totals.income : 1;
    if (ratio < 0.3)
      return "Ты копишь как бурундук перед зимой. Кеша впечатлён.";
    if (ratio < 0.6)
      return "Тратишь меньше половины дохода. Кеша одобряет твой самоконтроль.";
    if (ratio < 0.9)
      return "Баланс хороший, но Кеша советует присмотреться к подпискам.";
    if (ratio < 1.1) return "Тратишь почти всё. Кеша нервно грызёт жёлудь.";
    return "Расходы превышают доходы. Кеша в панике ищет твою заначку.";
  }, [totals]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-[300px] w-full rounded-xl" />
        <Skeleton className="h-[320px] w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Аналитика</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="py-8 text-center">
            <p className="text-sm text-kesha-expense mb-2">⚠️ {error}</p>
            <p className="text-xs text-kesha-text-secondary">
              Кеша не может загрузить данные для анализа. Проверь API.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Аналитика</CardTitle>
          {keshaInsight && (
            <p className="mt-1 text-xs text-kesha-accent italic leading-relaxed">
              🐿️ «{keshaInsight}»
            </p>
          )}
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex gap-1">
              {([3, 6, 12] as const).map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                    period === p
                      ? "bg-kesha-accent-bg text-kesha-accent"
                      : "bg-kesha-card-hover text-kesha-text-secondary"
                  }`}
                >
                  {p} мес.
                </button>
              ))}
            </div>
          </div>

          <div className="mt-4 flex items-center gap-4 py-2">
            <div className="flex-1">
              <p className="text-xs text-kesha-text-tertiary mb-1">Доход</p>
              <p className="text-lg font-semibold text-kesha-income tabular-nums">
                {formatCurrency(totals.income, "UAH")}
              </p>
            </div>
            <div className="flex-1">
              <p className="text-xs text-kesha-text-tertiary mb-1">Расход</p>
              <p className="text-lg font-semibold text-kesha-expense tabular-nums">
                {formatCurrency(totals.expense, "UAH")}
              </p>
            </div>
            <div className="flex-1">
              <p className="text-xs text-kesha-text-tertiary mb-1">Итог</p>
              <p
                className={`text-lg font-bold tabular-nums ${
                  netResult >= 0 ? "text-kesha-income" : "text-kesha-expense"
                }`}
              >
                {formatCurrency(netResult, "UAH")}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {transactions.length === 0 ? (
        <EmptyState variant="analytics" />
      ) : (
        <>
          <MonthlyChart transactions={transactions} months={period} />
          <CategoryPieChart transactions={transactions} />
          <PeriodCompare transactions={transactions} />
        </>
      )}
    </div>
  );
}
