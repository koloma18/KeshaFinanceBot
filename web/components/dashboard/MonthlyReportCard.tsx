"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { formatAmountInt, formatPercent } from "@/lib/formatters";
import { getCategoryEmoji } from "@/lib/category-emoji";
import type { SpendingByCategory } from "@/lib/types";

interface RecurringItem {
  title: string;
  amount: number;
}

interface MonthlyReportCardProps {
  monthLabel: string;
  income: number;
  expense: number;
  categories?: SpendingByCategory[];
  recurringTotal?: number;
  recurringItems?: RecurringItem[];
  loading?: boolean;
  empty?: boolean;
}

function keshaComment(net: number): string {
  if (net > 10000) return "Кеша гордится тобой. Шикарный месяц!";
  if (net > 0) return "Кеша доволен. Так держать.";
  if (net === 0) return "Месяц в ноль. Стабильность.";
  if (net > -5000) return "Кеша замечает утечку орехов.";
  return "Кеша в шоке от таких трат.";
}

export function MonthlyReportCard({
  monthLabel,
  income,
  expense,
  categories,
  recurringTotal,
  recurringItems,
  loading,
  empty,
}: MonthlyReportCardProps) {
  if (loading) {
    return <SkeletonCard />;
  }

  if (empty) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{monthLabel}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-kesha-text-secondary text-sm text-center py-4">
            Нет данных за этот месяц
          </p>
        </CardContent>
      </Card>
    );
  }

  const net = income - expense;
  const recPct =
    expense > 0 && recurringTotal ? (recurringTotal / expense) * 100 : 0;
  const hasRecurring = recurringItems && recurringItems.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{monthLabel}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-sm text-kesha-text-secondary">Доход</span>
          <span className="text-kesha-income font-semibold tabular-nums">
            +{formatAmountInt(income)} ₴
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-kesha-text-secondary">Расход</span>
          <span className="text-kesha-expense font-semibold tabular-nums">
            -{formatAmountInt(expense)} ₴
          </span>
        </div>
        <div className="border-t border-kesha-border pt-2 mt-1">
          <div className="flex justify-between items-center">
            <span className="text-sm text-kesha-text-secondary">Итог</span>
            <span
              className={`font-bold tabular-nums ${
                net >= 0 ? "text-kesha-income" : "text-kesha-expense"
              }`}
            >
              {net >= 0 ? "+" : ""}
              {formatAmountInt(net)} ₴
            </span>
          </div>
        </div>
        <p className="text-xs text-kesha-accent italic pt-1">
          🐿️ {keshaComment(net)}
        </p>

        {categories && categories.length > 0 && (
          <div className="border-t border-kesha-border pt-2 mt-2 space-y-1.5">
            <p className="text-xs text-kesha-accent font-medium">🏆 Топ трат</p>
            {categories.map((cat) => (
              <div key={cat.category}>
                <div className="flex items-center gap-1 text-xs">
                  <span className="text-kesha-text-primary truncate flex-1 min-w-0">
                    {getCategoryEmoji(cat.category)} {cat.category}
                  </span>
                  <span className="text-kesha-text-secondary shrink-0 tabular-nums">
                    {formatAmountInt(cat.amount)} ₴
                  </span>
                  <span className="text-kesha-text-tertiary shrink-0 tabular-nums w-9 text-right">
                    {formatPercent(cat.percentage)}
                  </span>
                </div>
                <div className="h-1.5 bg-kesha-border rounded-full mt-0.5 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-kesha-expense transition-all duration-500"
                    style={{ width: `${Math.min(cat.percentage, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {hasRecurring && (
          <div className="border-t border-kesha-border pt-2 mt-2 space-y-1">
            <p className="text-xs text-kesha-accent font-medium">
              🔁 Регулярные · {formatAmountInt(recurringTotal!)} ₴
              {recPct > 0 && ` · ${formatPercent(recPct)} расходов`}
            </p>
            {recurringItems!.map((item) => (
              <div key={item.title} className="flex justify-between text-xs">
                <span className="text-kesha-text-secondary truncate flex-1 min-w-0 mr-2">
                  • {item.title}
                </span>
                <span className="text-kesha-text-secondary shrink-0 tabular-nums">
                  {formatAmountInt(item.amount)} ₴
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
